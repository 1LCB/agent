class log:
    @staticmethod
    def blue(tag: str, text: str):
        print(f"\033[94m[{tag}]\033[0m {text}")
    
    @staticmethod
    def red(tag: str, text: str):
        print(f"\033[91m[{tag}]\033[0m {text}")
    
    @staticmethod
    def green(tag: str, text: str):
        print(f"\033[92m[{tag}]\033[0m {text}")
    
    @staticmethod
    def yellow(tag: str, text: str):
        print(f"\033[93m[{tag}]\033[0m {text}")
    
    @staticmethod
    def cyan(tag: str, text: str):
        print(f"\033[96m[{tag}]\033[0m {text}")
    
    @staticmethod
    def magenta(tag: str, text: str):
        print(f"\033[95m[{tag}]\033[0m {text}")

