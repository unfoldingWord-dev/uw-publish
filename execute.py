import sys

if __name__ == '__main__':
    args = sys.argv
    args.pop(0)

    if len(args) > 0:
        cmd = args[0]
        if cmd[-3:] != '.py':
            cmd += '.py'

        print cmd
        execfile('app_code/cli/' + cmd)
