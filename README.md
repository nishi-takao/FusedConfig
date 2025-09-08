# FusedConfig

NISHI, Takao <nishi.t.es@osaka-u.ac.jp>

## What's this?
FusedConfig provides a unified configuration definition and reference that integrates JSON files, environment variables, and command-line options for any Python program.

## Install
Clone this repository and copy `fusedconfig.py` to your project directory.

## Usage
For a quick guide, check out the test code at the end of [fusedconfig.py](fusedconfig.py).

### Configration Definition

```python

from fusedconfig import *

# create root section
config=FusedConfig()

# Define item `a` and set its default value to 0.
# This item is not associated with any environment
# variables or command-line options.
config.add_item('a',0)

# Define item `b` and set its default value to 1.
# This item is associated with `MYPROJ_VAR_B` environment
# variable and `-b` or `--var-b` command-line option.
config.add_item('b',1,
    envvar='MYPROJ_VAR_B',   # tied with environment variable
    argvar=['-b','--var-b'], # tied with command-line option
    type=int,                # You can use the same kwargs as
    choices=[0,1,2,3],       #   ArgumentParser#add_argument()
    help='set value to b'    #
)

config.add_item('c',2)

# Associations with items can be specified later.
config['c'].add_receiver(argvar=['-c','--var-c'],type=int)

# By naming items with a leading underscore ('_') or specifying hidden=True,
# you can create items that are not dumped to the dictionary.
# This is useful when deploying configuration files.
config.add_item('d','secret',hidden=True)
config.add_item('_e','***')

# Define section `Foo`.
# Sections are useful when you want to separate namespaces.
sec=config.add_section('Foo')

# Define item `f`under section `Foo`
sec.add_item('f',0)

# Of course, you can also define items with the same name as those
# defined in another section.
# However, the environment variables and command-line options associated
# with it must have unique names across all sections.
sec.add_item('b','b',
    argvar=['--var-a-b'], # Can not use `--var-b`
    type=str
)

```

### Saving
```python

with open('foo.json','w') as f:
    config.save(f)
```


### Loading / Applying
```python

# Load config file (JSON format)
with open('foo.json') as f:
    config.load(f)

# Apply environment variable
config.from_os()

# Build ArgumentParser and apply command-line options
parser=config.to_optargs
opts=parser.parse_args()
config.from_optargs(opts)

# When you want to do everything at once, do it like this:
config.parse(base_config_files='foo.json')

```

### Reading and Rewriting
```python

# readign as properties
config.a #=> 0
config.b #=> 1

# readign as dict
config['c'] #=> <FusedConfig.Item object>
config['c'].get() #=> 2 # same mean as config.c

# You can also read hidden items.
config.d #=> 'secret'

# However, items whose names begin with an underscore '_' cannot
# be read as properties.
#
# config._e #=> raise AttributeError
#
# You must retrieve the object in dict format
# and use the get() method.
config['_e'].get() #=> '***'


config.Foo #=> <FusedConfig object>
config.Foo.b #=> 'b'
config['Foo'].b #=> 'b'

# The values for each item can be changed as follows:
config.a=42
config['a'].set(42)
config.set(a=42,z=0) # Writing to an undefined `z` will be ignored.
```
