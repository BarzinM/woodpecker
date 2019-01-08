# Woodpecker

A program to help with music playing practice routines. For each practice in a given sequence of practices, it plays a metronome sound with specified tempo for the indicated duration. It will then move to the next practice.

Image of the interface:

![user interface](https://gitlab.com/BarzinM/practice/raw/master/interface_image.png)

Name of the practice comes at the top. It shows the tempo (bpm) and time remaining for the current practice. At the bottom, it shows how many minutes is left for all the remaining practices in your practice routine.


## Dependencies

Install python dependencies:

```
sudo pip3 install ruamel.yaml
sudo pip3 install pygame
```

Also, you need to have the light-weight audio player called `paplay`. It seems that Linux operating systems already have it installed. If Mac devices don't have `paplay`, it can be installed through `brew install pulseaudio`. 

## Usage

To simply play a metronome:
```
python3 main.py dry
```

To follow a practice routine:
```
python3 main.py <practice_file_name.yaml>
```

## Setting up a practice routine
You should make a YAML file that has a structure similar to:
```yaml
name of first practice:
    bpm: 60 # or any other number
    time: 3 # duration of practice in minutes

name of second practice:
    bpm: 80
    time: 4 # in minutes

name of third practice:
    bpm: 0 # zero means don't play tic sound for this practice.
    time: 10

name of fourth practice:
    bpm: 40
    time: 4
    rate: 5 # rate of each practice is optional. Means increase the bpm with a rate of 5 bpm per hour of practice.
```
## Controls
While running, the following keys can be used to control different properties:
- `Esc`: exit the program.
- `up/down arrows`: increase/decrease metronome bpm.
- `Ctrl + up/down arrows`: increase/decrease metronome bpm in increments of 5.
- `left/right arrows`: go to previous/next practice.
- `space`: pause/continue practice.
- `+/-`: increase/decrease volume.

## Settings
The `settings.yaml` contains some configuration settings:
```yaml
scale: 2. # makes the user interface larger or smaller.
rest_time: 5 # seconds between each practice so that you can prepare for next one.
file_path: "" # optional. It's the path to the YAML practice file so that you don't need to add it as an argument in command line.
```

## Notes
If you don't provide an argument for practice information and the `settings.yaml` file also doesn't contain a path to a practice file, the program tries to find a yaml file in the directory that it was called from.