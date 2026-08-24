# VHS tape (https://github.com/charmbracelet/vhs) recording a real, live
# session against microcenter.com -- not staged/mocked data. Regenerate with:
#   vhs docs/demo.tape
# Requires a working `mcenter session status` first (see README) -- the one
# step this can't show, since solving the Cloudflare checkbox needs a real
# human in a real browser and can't be scripted deterministically.

Output docs/demo.gif

Set Shell "zsh"
Set FontSize 16
Set Width 1200
Set Height 1000
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 40ms

Type "mcenter --help"
Enter
Sleep 2s

Type "mcenter session status"
Enter
Sleep 2s

Type "mcenter stores find cambridge"
Enter
Sleep 1500ms

Type `mcenter search "rtx 5090" --store 121 --sort price-low --in-stock-only --max-price 4400 --exclude backplate --exclude "water block" --exclude laptop --exclude "gaming pc"`
Enter
Sleep 3s

Type "mcenter product 693517 --store 121"
Enter
Sleep 2500ms

Type "mcenter product 693517 --store 121 --json"
Enter
Sleep 3s
