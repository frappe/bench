from sys import platform

if platform == "linux" or platform == "linux2":
    op_sys="linux"
elif platform == "darwin": #check what is the output for macOS
    op_sys="macOS"
elif platform == "win32":
    op_sys="Windows"

print(op_sys)