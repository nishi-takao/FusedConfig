#
# FusedConfig
#
# FusedConfig provides a unified configuration definition and reference
# that integrates JSON files, environment variables,
# and command-line options.
#
# NISHI, Takao <nishi.t.es@osaka-u.ac.jp>
# Time-stamp: <2025-09-02 14:54:20 zophos>
#
'''
    Copyright (c) 2025, NISHI, Takao
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY COPYRIGHT HOLDER ''AS IS'' AND ANY
    EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDER BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
import os
import inspect
import warnings
import argparse
import json

__all__=['FusedConfig']

########################################################################
#
#
#
class FusedConfig:
    
    ####################################################################
    #
    # configration item with command line argument and/or
    # environment var. difinition
    #
    class Item:
        Argparse_Kargs=[
            'option_strings',
            'dest',
            'nargs',
            'const',
            'default',
            'type',
            'choices',
            'help',
            'required',
            'metavar',
            'action',
        ]

        #
        #  parent : parent container
        #  name : configration item name
        #  value : default value 
        #  envvar : environment variable associated with this item
        #  argvar : command line options associated with this item
        #  set_func : function(obj,value) for writing value to obj
        #  get_func : function(obj) for reading value from obj
        #  hidden : when set True, this item will not dump to dict
        #  and other kwargs for ArgumentParser#add_argument()
        #
        def __init__(
            self,
            parent,
            name,
            value=None,
            *,
            envvar=None,
            argvar=None,
            set_func=None,
            get_func=None,
            hidden=None,
            **props
        ):
            self._parent=parent
            self._name=name
            self._value=value
            self._set_func=set_func
            self._get_func=get_func
            self._hidden=hidden
            self._envvar=None
            self._argvar=None
            self._destname=None
            self._props=None
            
            self._set_envprops(envvar,props)
            self._set_argprops(argvar,None)
            
            if(name is not None):
                if(value is None):
                    if('default' in props):
                        self.set(props['default'])
                    elif('const' in props):
                        self.set(props['const'])
                
                if((hidden is None) and (name[0]=='_')):
                    self._hidden=True
            
            
        def set(self,value,*,raw=False):
            if(self._set_func and not raw):
                self._set_func(self,value)
            else:
                self._value=value
            
            return self._value
        
        def get(self,*,raw=False):
            if(self._get_func and not raw):
                return self._get_func(self)
            else:
                return self._value
            
        def from_optargs(self,opts,*,allow_none=False):
            if((self._destname is not None) and \
               (self._destname in opts)):
                v=getattr(opts,self._destname)
                if(allow_none or (self.get() is None) or (v is not None)):
                    return self.set(v)
            
            return None
        
        def to_optargs(self,parser):
            if(self._argvar is None):
                return parser
            
            args=self._argvar
            kargs={
                k:self._props[k] \
                for k in self.__class__.Argparse_Kargs if k in self._props
            }

            ret=parser.add_argument(*args,**kargs)
            self._destname=ret.dest
            
            return parser
        
        def from_env(self,env=os.environ):
            if(self._envvar is None):
                return None
            if(self._envvar in env):
                v=env[self._envvar]
                if(('type' in self._props) and \
                   self._props['type'] is not None)):
                    v=self._props['type'](v)
                
                return self.set(v)
            
            return None
        
        def add_item(self,name,value=None,**props):
            return self._parent.add_item(name,value,**props)
        
        def add_handler(
                self,
                envvar=None,
                argvar=None,
                set_func=None,
                get_func=None,
                **props
        ):
            if(((envvar is not None) and (self._envvar is not None)) or \
               ((argvar is not None) and (self._argvar is not None)) or \
               ((set_func is not None) and (self._set_func is not None)) or \
               ((get_func is not None) and (self._get_func is not None))):
                return self._parent.add_handler(
                    self,
                    envvar=envvar,
                    argvar=argvar,
                    set_func=set_func,
                    get_func=get_func,
                    **props
                )
            
            if(envvar is not None):
                self._set_envprops(envvar,props)
            if(argvar is not None):
                self._set_argprops(argvar,props)
            if(set_func is not None):
                self._set_func=set_func
            if(get_func is not None):
                self._get_func=get_func
            
            return self
        
        def _set_envprops(self,envvar,props):
            self._envvar=envvar
            if(props is not None):
                if(('type' in props) and \
                   (props['type'] is not None) and \
                   (not callable(props['type'])):
                   raise ValueError(
                       'unknown type "%s"' % (props['type'].__name__)
                   )
                
                self._props=props
        
        def _set_argprops(self,argvar,props):
            self._argvar=argvar
            self._destname=None
            if(self._argvar is not None):
                if(not isinstance(self._argvar,(list,tuple))):
                    self._argvar=[self._argvar]
                self._destname=self._build_destname(*self._argvar,**props)
            
            if(props is not None):
                self._props=props
        
        #
        # copied from argparse.py
        # _ActionsContainer#_get_optional_kwargs()
        # https://github.com/python/cpython/blob/3.13/Lib/argparse.py#L1586C9-L1586C29
        #
        def _build_destname(self,*args,**kwargs):
            prefix_chars='-'
            
            # determine short and long option strings
            option_strings = []
            long_option_strings = []
            for option_string in args:
                # error on strings that don't start with an appropriate prefix
                if not option_string[0] in prefix_chars:
                    raise ValueError(
                        'invalid option string %s: '
                        'must start with a character %s' % (
                            option_string,
                            prefix_chars
                        )
                    )
                
                # strings starting with two prefix characters are long options
                option_strings.append(option_string)
                if len(option_string) > 1 and option_string[1] in prefix_chars:
                    long_option_strings.append(option_string)
                
            # infer destination, '--foo-bar' -> 'foo_bar' and '-x' -> 'x'
            dest = kwargs.pop('dest', None)
            if dest is None:
                if long_option_strings:
                    dest_option_string = long_option_strings[0]
                else:
                    dest_option_string = option_strings[0]
                dest = dest_option_string.lstrip(prefix_chars)
                if not dest:
                    msg = _('dest= is required for options like %r')
                    raise ValueError(msg % option_string)
                dest = dest.replace('-', '_')

            return dest
    #
    # end of FusedConfig.Item
    #
    ####################################################################

    ####################################################################
    #
    # Command line argument/Env var. handler without entity.
    # This class instances do NOT have own name and value.
    #
    class Handler(Item):
        #
        #  dst : destination object for sending value
        #  envvar : environment variable associated with this item
        #  argvar : command line options associated with this item
        #  set_func : function(obj,value) for writing value to obj
        #  get_func : function(obj) for reading value from obj
        #  and other kwargs for ArgumentParser#add_argument()
        #
        def __init__(
            self,
            dst,
            *,
            envvar=None,
            argvar=None,
            set_func=None,
            get_func=None,
            **props
        ):
            if((envvar is None) and \
               (argvar is None) and \
               (set_func is None) and \
               (get_func is None)):
                raise TypeError(
                    'One or more of the keywords argvar, '
                    'envvar, set_func, or get_func is required.'
                )
            
            self._dst=dst
            super().__init__(
                self._dst._parent,
                None,
                None,
                envvar=envvar,
                argvar=argvar,
                set_func=set_func,
                get_func=get_func,
                **props
            )
            
            del self._name  # remove own name and value
            del self._value
            
        def set(self,value,*,raw=False):
            if(self._set_func and not raw):
                self._set_func(self._dst,value)
            else:
                self._dst.set(value,raw=raw)
        
        def get(self,*,raw=False):
            if(self._get_func and not raw):
                return self._get_func(self._dst)
            else:
                return self._dst.get(raw=raw)

        def add_handler(self,**props):
            return self._parent.add_handler(self._dst,**props)

    #
    # end of FusedConfig.Handler
    #
    ####################################################################
                
    #
    #  parent : parent container
    #  name : configration section name
    #  description: description of this section (will use in argparser)
    #
    def __init__(self,parent=None,name=None,description=None,hidden=None):
        self._parent=parent
        self._name=name
        self._description=description
        self._items={}
        self._sections={}
        self._hidden=hidden
        if((name is not None) and (hidden is None) and (name[0]=='_')):
            self._hidden=True

    def __getattr__(self,name):
        if(name in self.public_items):
            return self._items[name]._value
        elif(name in self.public_sections):
            return self._sections[name]
        
        raise AttributeError(
            "The object has no attribute '%s'"%(name)
        )

    def __setattr__(self,name,value):
        #
        # When this method is calling from outside
        #
        # I know I'm using black magic
        locals_=inspect.stack()[1].frame.f_locals
        if(('self' not in locals_) or (locals_['self']!=self)):
            #
            # case of the item
            #
            if(name in self.public_items):
                return self._replace_item(name,value)
            #
            # case of the section
            #
            elif(name in self.public_sections):
                return self._replace_section(name,value)
            
        #
        # Default (within calling from inside)
        #
        return super().__setattr__(name,value)
    
    #
    # allow class/function-like behavior
    #
    def __call__(self):
        return self

    #
    # allow container-like behavior
    #
    def __len__(self):
        return len(self._items)+len(self._sections)
    
    def __contains__(self,key):
        return key in self.all_entries
    
    def __getitem__(self,key):
        return self.all_entries[key]

    def __setitem__(self,name,value):
        if(name in self._items):
            self._replace_item(name,value)
        elif(name in self._sections):
            self._replace_section(name,value)
        elif(isinstance(value,self.__class__.Item)):
            name=self._chk_name_consistency(name,value)
            self._add_item(value)
        elif(isinstance(value,self.__class__)):
            name=self._chk_name_consistency(name,value)
            if(name in self._sections):
                raise KeyError('%s is in used'%(name))
            self._sections[name]=value
        else:
            self.add_item(name,value)

    @property
    def public_items(self):
        return self._keyname_filter(self._items)
    
    @property
    def public_sections(self):
        return self._keyname_filter(self._sections)

    @property
    def public_entries(self):
        d=self.public_items
        d.update(self.public_sections)
        return d
    
    @property
    def all_entries(self):
        d={k:v for k,v in self._items.items()}
        d.update({k:v for k,v in self._sections.items()})
        return d
    
    def get(self,name,*,raw=False):
        if(name in self._items):
            return self._items[name].get(raw=raw)
        
        raise KeyError(name)
    
    def set(self,raw=False,**kwargs):
        for k,v in kwargs.items():
            if(k in self._items):
                self._items[k].set(v,raw=raw)
            else:
                warnings.warn(
                    "'%s' does not exist. ignored."%(k),
                    UserWarning,
                    stacklevel=2
                )
    
    def add_item(self,name,value=None,**props):
        item=self.__class__.Item(self,name,value,**props)
        return self._add_item(item)
    
    def add_handler(self,dst,**props):
        item=self.__class__.Handler(dst,**props)
        self._add_item(item)
        return dst
    
    def add_section(self,name,description=None,hidden=None):
        if(name is None):
            return self
        elif(name in self._sections):
            raise KeyError('%s is in used'%(name))
        
        sec=self.__class__(self,name,description,hidden)
        self._sections[name]=sec
        return sec
    
    def from_optargs(self,opts):
        for v in self._items.values():
            v.from_optargs(opts)
        
        for v in self._sections.values():
            v.from_optargs(opts)
        
        return self
    
    def to_optargs(self,parser=None):
        if(parser is None):
            parser=argparse.ArgumentParser(
                description=self._description
            )
        elif(isinstance(parser,argparse.ArgumentParser) and \
             (self._name is not None)):
            # avoiding nesting argument groups (has been deprecated)
            parser=parser.add_argument_group(
                self._name,
                description=self._description
            )
        
        for v in self._items.values():
            v.to_optargs(parser)
        
        for v in self.public_sections.values():
            v.to_optargs(parser)
        
        return parser
    
    def from_env(self,env=os.environ):
        for v in self._items.values():
            v.from_env(env)
            
        for v in self._sections.values():
            v.from_env(env)

        return self
    
    def from_dict(self,d,*,raw=False):
        for k,v in d.items():
            if(k in self._items):
                self._items[k].set(v,raw=raw)
            elif(k in self._sections):
                self._sections[k].from_dict(d[k],raw=raw)
        
        return self
            
    def to_dict(self,*,raw=False,with_hidden_item=False):
        d={}
        for k,v in self.public_items.items():
            if(with_hidden_item or (not v._hidden)):
                d[k]=v.get(raw=raw)

        for k,v in self.public_sections.items():
            if(with_hidden_item or (not v._hidden)):
                d[k]=v.to_dict(raw=raw,with_hidden_item=with_hidden_item)

        return d
    
    def load(self,fp):
        return self.from_dict(json.load(fp))

    def save(self,fp,*,with_hidden_item=False):
        json.dump(
            self.to_dict(with_hidden_item=with_hidden_item),
            fp,
            indent=2
        )
        return self

    #
    # base_config_files : Configuration files to load initially
    # skip_env : When set to True, skip applying environment variables
    # skip_optparse : When set to True, skip applying command-line options
    # opt_file_arg : Command-line option name for specifying the config file
    # opt_args : Option strings for ArgumentParser#parse_args()
    #
    def parse(
            self,
            *,
            base_config_files=None,
            skip_env=False,
            skip_optparse=False,
            opt_file_arg=['--config-file'],
            opt_args=None
    ):
        if(base_config_files is not None):
            if(not isinstance(base_config_files,(list,tuple))):
                base_config_files=[base_config_files]
            for f in base_config_files:
                if(os.path.exists(f)):
                    try:
                        with open(f) as fp:
                            self.load(fp)
                        break
                    except Exception:
                        pass
        
        if(not skip_optparse):
            parser=self.to_optargs()
            cf_attr=None
            if(opt_file_arg):
                if(not isinstance(opt_file_arg,(list,tuple))):
                    opt_file_arg=[opt_file_arg]
                cf_attr=parser.add_argument(
                    *opt_file_arg,
                    help='path to configration file'
                ).dest
            opt=parser.parse_args(opt_args)
            
            if(cf_attr is not None):
                cf=getattr(opt,cf_attr)
                if(cf is not None):
                    with open(cf) as fp:
                        self.load(fp)
        
        if(not skip_env):
            self.from_env()
        self.from_optargs(opt)
        
        return self
    
    def _add_item(self,item):
        name='_%d'%(len(self._items))
        if(('_name' in vars(item)) and (item._name is not None)):
            name=item._name
        if name in self._items:
            raise KeyError('%s is in used'%(name))
        
        self._items[name]=item
        
        return item
    
    def _replace_item(self,name,value):
        if(isinstance(value,self.__class__.Item)):
            if(name==value._name):
                self._items[name]=value
            else:
                raise ArgumentError(
                    'Name does not match %s and %s'%(
                        name,
                        value._name
                    )
                )
        else:
            self._items[name]._value=value
            
        return self._items[name]

    def _replace_section(self,name,value):
        if(isinstance(value,self.__class__)):
            if(name==value._name):
                self._sections[name]=value
            else:
                raise ArgumentError(
                    'Name does not match %s and %s'%(
                        name,
                        value._name
                    )
                )
        else:
            raise TypeError(
                'The section item shold be FusedConfig object'
            )

        return self._sections[name]

    def _keyname_filter(self,dic):
        return { k:dic[k] for k in dic.keys() if k[0]!='_' }

    def _chk_name_consistency(self,name,value):
        if('_name' in var(value)):
            if(name!=value._name):
                warnings.warn(
                    "'%s' will be replaced to '%s'."%(name,value._name),
                    UserWarning,
                    stacklevel=2
                )
            return value._name
        else:
            return name

#
# end of FusedConfig
#
########################################################################

if(__name__=='__main__'):

    # difinition
    c=FusedConfig()
    c.add_item('x',-1)
    c.add_item('_y',-2) # this will not dumps to dict
    c.add_item('z',3,hidden=True) # ditto
    
    # section
    s=c.add_section('Hoge')
    s.add_item('num',0,argvar=['-n','--num'],type=int) # with cmd-line option
    s.add_item('str','0').add_handler(argvar=['-s','--str'])
    s.add_item('home',argvar=['--home'],envvar='HOME') # with env.var reference
    
    # yet another section
    s=c.add_section('Hage','hogehohe')
    s.add_item('foo','foo',argvar=['--foo'],type=str)
    s.add_item('bar',False,argvar=['-b','--bar'],
               action='store_true',help='store true')

    # hidden section
    s=c.add_section('Moge',hidden=True)
    s.add_item('baz',None)

    
    # read accsess
    print(c.to_dict())

    print(c.Hoge().to_dict()) # partial dump
    print(c.Hoge.num) # direct access

    # dict-like accessing returns item/section object instead of the value
    o=c['Hage']['foo']
    # value of the item object can access using get() method
    print(o.get())
    
    try:
        print(c._y)
    except AttributeError:
        print('You can not access to hidden items direct')
    
    print(c['_y'].get()) # dict-like accessing allows hidden item

    
    # apply env.vars. and command-line options
    c.parse(
        base_config_files=None,
        opt_args=['-n','3']
    )

    d=c.to_dict()
    print(d)

    
    # rewrite dict and apply it
    d['Hoge']['num']=4
    c.from_dict(d)
    
    #
    # 4 way of rewriting value
    #
    c.x=34
    c['Hoge']['str'].set('x')
    c.Hoge['num']=42
    c.Hoge.set(home=None,hage=0)
    print(c.to_dict())

    #
    # saving
    #
    with open('.demo.fusedconfig.json','w') as f:
        c.save(f)

    #
    # loading
    #
    with open('.demo.fusedconfig.json') as f:
        c.load(f)
    
    #
    # show the help message and exit
    #
    parser=c.to_optargs()
    parser.parse_args(['-h'])
    
