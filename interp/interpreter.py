import random
from abc import ABC
from abc import abstractmethod
from inspect import signature
from typing import Callable
from typing import Optional
from typing import Tuple
import textwrap

from lark import LarkError
from tabulate import tabulate

from interp.parser import Expression
from interp.parser import Id
from interp.parser import Parser


class InterpException(Exception):
    def __init__(self, msg, priority=100):
        super(InterpException, self).__init__()
        self.msg = msg
        self.priority = priority  # 0 is highest priority


class BoundExpression:
    def __init__(self, method: Callable, args: list, kwargs: dict, assignment: Optional[str]):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.assignment = assignment

    def __call__(self):
        return self.method(*self.args, **self.kwargs)


class Interpretable(ABC):

    @abstractmethod
    def bind(self, method: str, args: list, kwargs: dict, assignment) -> BoundExpression:
        pass


class InterpretableWrapper(Interpretable):
    __builtin = ["options"]

    def __init__(self, obj):
        # TODO: warn if a __builtin is overridden
        self._obj = obj

    def options(self):
        # TODO: should be able to explain a single method, maybe also have a verbose mode which prints out the
        # method doc string

        def inspect_fn(fn):
            sig = signature(fn)
            # TODO add default params
            return [k for k in sig.parameters.keys()]

        def inspect_obj(obj):
            methods = {}
            for field in filter(lambda field: not field.startswith("_") and callable(getattr(obj, field)), dir(obj)):
                methods[field] = inspect_fn(getattr(obj, field))
            return methods

        target = self._obj
        lines = [f"type: {type(target)}", "functions:"]
        indent = '  '
        indent_level = 1
        for method, args in inspect_obj(target).items():
            method = method.replace("_", " ")
            lines.append(f"{indent * indent_level}{method}")
            indent_level += 1
            for idx, arg in enumerate(args):
                lines.append(f"{indent * indent_level}{arg}")
            indent_level -= 1
        return lines

    def bind(self, method: str, args: list, kwargs: dict, assignment) -> BoundExpression:
        _method = None
        if hasattr(self._obj, method):
            _method = getattr(self._obj, method)
        elif method in InterpretableWrapper.__builtin:
            _method = getattr(self, method)

        if _method is None or not callable(_method):
            raise InterpException(f"no callable function '{method}' was found", 20)

        sig = signature(_method)
        try:
            sig.bind(*args, **kwargs)
            return BoundExpression(_method, args, kwargs, assignment)
        except TypeError:
            raise InterpException(f"the given arguments did not bind to function {method}", 10)


class Interpreter:

    def __init__(self, apps={}):
        self._parser = Parser()
        self._iself = InterpretableWrapper(self)
        self._target = self._iself
        self._vars = {}
        self._apps = apps
        self._session = []

    def _resolve_references(self, args: Optional[list], kwargs: Optional[dict]) -> Tuple[list, dict]:
        """
        Resolves any Id's found in the given arguments
        :param args:
        :param kwargs:
        :return:
        """
        def resolve_id(action, id_):
            if isinstance(id_, Id):
                if id_.value not in self._vars:
                    raise InterpException(f"argument {id_.value} was not a known variable")
                else:
                    var = self._vars[id_.value]
                    if isinstance(var, InterpretableWrapper):
                        action(var._obj)
                    else:
                        action(var)
            else:
                action(id_)

        resolved_args = []
        for a in [] if not args else args:
            resolve_id(lambda x: resolved_args.append(x), a)

        resolved_kwargs = {}

        def setter(k):
            def method(v):
                resolved_kwargs[k] = v
            return method

        for k, v in {}.items() if not kwargs else kwargs.items():
            resolve_id(setter(k), v)

        return resolved_args, resolved_kwargs

    def _resolve_expression(self, exp: Expression) -> BoundExpression:
        def refs():
            return self._resolve_references(exp.args[0], exp.args[1])

        if exp.target:
            if exp.target not in self._vars:
                raise InterpException(f"unable to find variable {exp.target}", 20)
            else:
                _target = self._vars[exp.target]
                # TODO: don't assume all targets are Interpretable
                return _target.bind(exp.method, *refs(), assignment=exp.assignment)

        # try to bind against the current target, if that fails, bind against self, if that fails return the first
        # exception encountered.
        candidates = [self._target, self._iself]
        ex = []
        for candidate in candidates:
            if not isinstance(candidate, Interpretable):
                continue
            try:
                return candidate.bind(exp.method, *refs(), assignment=exp.assignment)
            except InterpException as e:
                ex.append(e)
        sorted(ex, key=lambda e: e.priority)
        raise ex[0]

    def _call_expression(self, method: BoundExpression):
        try:
            r = method()
        except InterpException as e:
            raise e
        except Exception as e:
            raise InterpException(f"execution error, {str(e)}")

        # TODO: handle more interesting return scenarios. Could imagine wrapping the returned object and re-executing
        # For now, simply print strings and assign interpretables
        if method.assignment is not None:
            if isinstance(r, (str, list, dict, set)) or isinstance(r, Interpretable):
                self._vars[method.assignment] = r
            else:
                self._vars[method.assignment] = InterpretableWrapper(r)
        else:
            self.show(r)

    def __call__(self, statement):
        try:
            def bind(exp: Expression):
                try:
                    bound = self._resolve_expression(exp)
                    return bound, 0, "success"
                except InterpException as e:
                    return None, e.priority, e.msg

            bindings = list(sorted(map(bind, self._parser.parse(statement)), key=lambda x: x[1]))
            if not bindings:
                return None
            binding = bindings[0]

            if binding[1] != 0:
                print("failed to find a viable binding, " + binding[2])
            else:
                self._call_expression(binding[0])
                self._session.append(statement)

        except LarkError as e:
            print(f"there was an error parsing your input, {e}")
        except InterpException as e:
            print(f"{e.msg}")
        except Exception as e:
            print(f"there was some execution error, {e}")

    # built-in functions

    def create(self, name):
        if name in self._apps:
            return self._apps[name](self)  # TODO: not sure what if anything we should pass to the app
        raise InterpException(f"requested non-existent app type {name}. Options are {[x for x in self._apps.keys()]}")

    def delete(self, name):
        if name in self._vars:
            del self._vars[name]
        else:
            raise InterpException(f"there's no variable called {name}")

    def drop_target(self):
        self._target = self._iself

    def clear_session(self):
        self._session.clear()

    def save_session(self, path=""):
        filepath = path + "/session.txt"
        with open(filepath, 'w') as f:
            for line in self._session:
                f.write(line + "\n")
        return f"saved to {filepath}"

    def list(self):
        return list(self._apps.keys())

    def show(self, var_or_ref):
        if isinstance(var_or_ref, str) and var_or_ref in self._vars:
            # TODO: this is very hacky, requires a disambiguation flow
            var = self._vars[var_or_ref]
        else:
            var = var_or_ref

        def print_wrap(s):
            if isinstance(s, str):
                for line in textwrap.wrap(s):
                    print(line)
            else:
                print(s)

        if isinstance(var, list) and len(var) > 0 and isinstance(var[0], list):
            print(tabulate(var[1:], headers=var[0]))
        elif isinstance(var, list) or isinstance(var, set):
            for v in var:
                print(v)
        elif isinstance(var, str):
            print_wrap(var)
        elif var is not None:
            print_wrap(var)
        else:
            print("<none>")

    def use(self, varname):
        if varname in self._vars:
            self._vars['previousTarget'] = self._target
            self._target = self._vars[varname]
        else:
            raise InterpException(f"requested target {varname} was not in variables. Use 'options' to see variables")

    def options(self, obj=None) -> str:
        def get_target():
            if self._target == self._iself or self._target is None:
                return self
            else:
                return self._target

        def inspect_fn(fn):
            sig = signature(fn)
            # TODO add default params
            return [k for k in sig.parameters.keys()]

        def inspect_obj(obj):
            methods = {}
            for field in filter(lambda field: not field.startswith("_") and callable(getattr(obj, field)), dir(obj)):
                methods[field] = inspect_fn(getattr(obj, field))
            return methods


        target = get_target()
        lines = [f"target type:\n  {type(target)}\nfunctions:\n"]
        for method, args in inspect_obj(target).items():
            method = method.replace("_", " ")
            if args:
                lines.append(f"  {method} (")
                for idx, arg in enumerate(args):
                    if idx == len(args) - 1:
                        sep = ")\n"
                    else:
                        sep = ", "
                    lines.append(f"{arg}{sep}")
            else:
                lines.append(f"  {method}\n")

        lines.append("vars:\n")
        for var in self._vars.keys():
            lines.append(f"  {var}\n")

        return "".join(lines)

    def exit(self):
        print(random.choice(['goodbye!', 'see you later!', 'adios!', 'ciao!', 'bye!']))
        exit(0)
