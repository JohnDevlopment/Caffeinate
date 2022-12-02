# Caffeinate
Don't let your computer go to sleep while you're busy thinking.

# Why would I need this?
Software engineering is more about thinking than typing. And it's very annoying when you're whiteboarding or just thinking and your work machine goes to sleep. Most of the times, we don't have admin access to change the settings so this helps prevent the computer from going to sleep.

# Installation
Using pip:

``` sh
pip install caffeinate
```

Using pip3:

``` sh
pip3 install caffeinate
```

Doing this installs the original version from [subash774's github](https://github.com/subash774/Caffeinate).
You have to use the `setup.py` script found here in the repository in order to install this version.

``` sh
python3 setup.py build
python3 setup.py install
```

# Usage
| :memo:        | Tested on OSX and Windows       |
|---------------|:------------------------|

On windows, you might need to create a simple python file (code below) as path variable seems to be admin restricted.

``` python
from caffeinate import caffeinate

caffeinate.run()
```

On Linux or Mac OSX, you can simply type ```awake``` in the terminal.

# Termination
To terminate the process, press ```Esc``` key 3 consecutive times (doesn't have to be terminal focused key presses).

# TODO
* [ ] Add good documentation to the usage with params explained
* [X] Cleanup the code, maybe use classes for extensibility
