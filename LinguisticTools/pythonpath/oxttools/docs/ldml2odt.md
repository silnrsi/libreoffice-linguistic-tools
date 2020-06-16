# Using ldml2odt

ldml2odt takes an LDML file and a template and generates a report from it.

An example usage is:

```
scripts/ldml2odt -l pcm-Latn-NI -t reports/simple_report.fodt ~/path/to/sldr/flat/p/pcm_Latn.xml pcm_Latn.fodt
```

The various components of this command are:

- `-l` specifies a full language tag from which components can be extracted for parts fo the report.
- `-t` specifies the template to use. Templates are in the reports/ sudirectory of this project
-  The path to an LDML file. The best results are if the file is flattened in which case fallback values will
   also appear in the report. Non flat will just give blank values.
-  The output file to generate that can loaded into libreoffice.

## Writing Reports

This section describes the hidden fields syntax elements.

#### value

```value <xpath>```

#### variable

```variable <varname> <xpath>```

#### condvar

```condvar <varname> <xpath> [<testval>=<val>]*```

#### forenum forstr for endfor

```
for <mode> <varname> <xpath>
forstr <mode> <varnmae> <xpath>
forenum <mode> <varname> [value]*
```

Runs until

```endfor <varname>```

#### ifin endif

```ifin <mode> <ident> <xpath> <str>```

Runs until 

```endif <ident>```

### Functions

#### doc

```doc(path)```

#### firstword

```firstword(value)```

Returns first word in value.

#### findsep

```findsep(value, index)```

Returns indexth word of value.

#### replace

```replace(value, regexp, replace)```

Does re.sub(regexp, replace, value).

#### dateformat

```dateformat(value, format [, format]*)```

Currently does nothing and just returns value. Meant for converting dates and times from LDML into libo.

#### choose

```choose(test, a, b)```

Returns a if test else b

#### split

```split(vals*)```

Chops all the values into words and returns an array of them

#### default

```default(vals*)```

Returns an array of all non-empty values

#### concat

```concat(a, b)```

Returns concatenation of two strings

#### set

```set(vals*)```

Takes all the elements of all the values and returns a sorted unique list of them
