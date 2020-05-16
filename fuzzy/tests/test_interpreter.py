from fuzzy.interp.interpreter import InterpretableWrapper


class Command:

    def run_test(self, num, xxx, iterations= 2):
        """!
        This is a fake method to test the interpretable wrapper.
        num: This is an argument called num.
        iterations: This is another argument, this time with a default value.
        """
        return ""


def test_options():
    wrapped = InterpretableWrapper(Command)
    lines = wrapped.options()
    for line in lines:
        print(line)


