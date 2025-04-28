# Terminal ANSI color codes

class fg:
    BLACK   = '\033[30m'
    RED     = '\033[31m'
    GREEN   = '\033[32m'
    YELLOW  = '\033[33m'
    BLUE    = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN    = '\033[36m'
    WHITE   = '\033[37m'
    RESET   = '\033[39m'

    # 256 color mode (foreground)
    @staticmethod
    def color_256(n: int) -> str:
        return f'\033[38;5;{n}m'  # n should be in range(0, 256)

class bg:
    BLACK   = '\033[40m'
    RED     = '\033[41m'
    GREEN   = '\033[42m'
    YELLOW  = '\033[43m'
    BLUE    = '\033[44m'
    MAGENTA = '\033[45m'
    CYAN    = '\033[46m'
    WHITE   = '\033[47m'
    RESET   = '\033[49m'

    # 256 color mode (background)
    @staticmethod
    def color_256(n: int) -> str:
        return f'\033[48;5;{n}m'  # n should be in range(0, 256)

class style:
    RESET_ALL    = '\033[0m'
    BRIGHT       = '\033[1m'
    BOLD         = '\033[1m'  # alias for BRIGHT
    DIM          = '\033[2m'
    ITALIC       = '\033[3m'
    UNDERLINE    = '\033[4m'
    BLINK        = '\033[5m'
    INVERSE      = '\033[7m'
    HIDDEN       = '\033[8m'
    STRIKETHROUGH= '\033[9m'

    # Reset individual styles
    RESET_BRIGHT       = '\033[22m'
    RESET_BOLD         = '\033[22m'  # same as RESET_BRIGHT
    RESET_ITALIC       = '\033[23m'
    RESET_UNDERLINE    = '\033[24m'
    RESET_BLINK        = '\033[25m'
    RESET_INVERSE      = '\033[27m'
    RESET_HIDDEN       = '\033[28m'
    RESET_STRIKETHROUGH= '\033[29m'

if __name__ == "__main__":
    print(f"{style.BRIGHT}{fg.color_256(202)}Hello, Bright Orange!{style.RESET_ALL}")
    print(f"{bg.color_256(28)}{fg.color_256(231)}Inverted Terminal Box{style.RESET_ALL}")
