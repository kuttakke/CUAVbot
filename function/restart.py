import sys
import os


class Restart:

    @classmethod
    def restart_program(cls):
        """Restarts the current program.
        Note: this function does not return. Any cleanup action (like
        saving data) must be done before calling this function."""
        print('ready to restart program......')
        python = sys.executable
        os.execl(python, python, *sys.argv)
