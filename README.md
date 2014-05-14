MassMailer
==========

Mass Mailer in Python.  This script allows you to send a specified
quantity of the same e-mail in an automated fashion.

Dependencies
============

  Python 2.7 
  
  The excellent mailer library
    
    https://pypi.python.org/pypi/mailer/0.7

How To Use
==========

MassMailer can read in the required information for sending mail
from a config file (MassMailer.conf is an example containing all
required fields) or from the command line (run ./MassMailer.py -h
to see the command line options available).

All command line arguments override their value in the config file.
To specify a config file use the --config option.

Sample Usage
============

As an example, this would send 100 e-mails with random content in them
with 10 e-mails sent per connection:

```
./MassMailer.py -s smtp.gmail.com -u example@gmail.com --to friendlyneighbor@gmail.com -q 100 -n 10 -z```
```

This would send the same thing, but with all options in a config file:

```
./MassMailer.py --config MassMailer.conf
```
