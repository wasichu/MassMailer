#!/usr/bin/env python

# Imports
import argparse as ap
from ConfigParser import SafeConfigParser as cp
from getpass import getpass as gp
import inspect
import json
import os
import random
from string import printable 
import sys
import time

import mailer

def is_float_str(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
      
def is_list_str(s):
  try:
    list(s)
    return True
  except:
    pass

  try:
    l = json.loads(s)
    return type(l) == list
  except:
    return False
def rand_string(alphabet=printable, len_min=1, len_max=6):
  length = random.randint(len_min, len_max)
  s = ''
  for n in range(length):
    s += random.choice(alphabet)
  return s

class MassMailer(object):
  # Seed PRNG at class creation
  random.seed()

  def __init__(self, config_file='MassMailer.conf'):
    '''
    MassMailer constructor.
    
    Takes a path to a config file compatible with
    Python's ConfigParser standard library module.
    Defaults to a .conf file named after this class
    in the same directory as this module.
    '''
    # If necessary, open the config file
    if os.path.isfile(config_file):
        self.cp = cp()
        self.cp.read(config_file)
    
        # Parse the config file
        self.parseConfig()
    
    # Otherwise, read in defaults from the
    # command line
    else:
        self.parseArgs()
    
  def parseConfig(self):
    '''
    Go through each section of the config file and
    save each name, value pair as an attribute of
    the form:
    
        self.<section name>_<name>
    '''
    for section in self.cp.sections():
      for opt in self.cp.options(section):
        v = self.cp.get(section, opt)
        if v.lower() == 'yes' or v.lower() == 'no':
            v = True if v.lower() == 'yes' else False
        elif v and all(map(str.isdigit, v)):
            v = int(v)
        elif v and is_float_str(v):
            v = float(v)
        elif v and is_list_str(v):
            v = list(v)
        
        setattr(self, '_'.join((section, opt)), v)

  def saveConfigFile(self, cf='MassMailer.conf', pw=False):
    '''
    Save all passed in command line arguments
    and user input to the config file specified
    by cf.  pw is a boolean that controls whether
    the password gets saved to the config.
    '''
    with open(cf, 'w') as cpf:
      self.cp = cp()
      for member in self.__dict__:
        member_obj = getattr(self, member)
        if '_' in member and not inspect.ismethod(member_obj):
          section = member.split('_')[0]
          name = member[member.find('_')+1:]
          val = getattr(self, member)
          if val is None:
            val = ''

          if name == 'password':
            if not pw:
              val = ''

          # Save values in the SafeConfigParser object
          if section not in self.cp.sections():
            self.cp.add_section(section)
          self.cp.set(section, name, str(val))
      # Write to the file
      self.cp.write(cpf)
     
  def parseArgs(self):
      '''
      In the absence of a config file, read in command
      line arguments to set the necessary values for 
      the MassMailer object
      '''
      if hasattr(self, 'cp'):
          return
          
      # Get a Namespace args
      args = self.getParsedArgs()

      for n, v in vars(args).iteritems():
        setattr(self, n, v)

  def getParsedArgs(self):
      '''
      Parses command line args and returns the result
      of calling the parse_args method on the ArgumentParser
      object built below.
      '''
      self.cp = ap.ArgumentParser( 
          formatter_class=ap.ArgumentDefaultsHelpFormatter)
      
      # SMTP options
      self.cp.add_argument( '-s'
                          , '--server'
                          , help='SMTP server\'s hostname'
                          , dest='smtp_server'
                          , required=True
                          )
      self.cp.add_argument( '-p'
                          , '--port'
                          , type=int
                          , default=587
                          , help='SMTP server\'s port'
                          , dest='smtp_port'
                          )
      self.cp.add_argument( '-u'
                          , '--username'
                          , help='SMTP username'
                          , dest='smtp_username'
                          , required=True
                          )
      self.cp.add_argument( '-w'
                          , '--password'
                          , help='SMTP password'
                          , dest='smtp_password'
                          )
      self.cp.add_argument( '-t'
                          , '--tls'
                          , action='store_true'
                          , default=True
                          , dest='smtp_tls'
                          , help='Whether to use TLS'
                          )

      # Message Options
      self.cp.add_argument( '-r'
                          , '--to'
                          , nargs='+'
                          , help='Email addresses to send to'
                          , dest='message_to'
                          , required=True
                          )
      self.cp.add_argument( '-c'
                          , '--cc'
                          , nargs='+'
                          , dest='message_cc'
                          , help='E-mail CC list'
                          )
      self.cp.add_argument( '-b'
                          , '--bcc'
                          , nargs='+'
                          , dest='message_bcc'
                          , help='E-mail BCC list'
                          )
      self.cp.add_argument( '-f'
                          , '--from'
                          , dest='message_from'
                          , help='From address'
                          )
      self.cp.add_argument( '-j'
                          , '--subject'
                          , dest='message_subject'
                          , help='Message subject'
                          )
      self.cp.add_argument( '-d'
                          , '--date'
                          , dest='message_date'
                          , help='Date header field'
                          )
      self.cp.add_argument( '-l'
                          , '--html'
                          , dest='message_html'
                          , action='store_true'
                          , default=False
                          , help='Whether to compose an HTML message'
                          )
      self.cp.add_argument( '-a'
                          , '--attachments'
                          , dest='message_attachments'
                          , nargs='+'
                          , help='List of files to attach to mail'
                          )
      self.cp.add_argument( '-m'
                          , '--message'
                          , dest='message_body'
                          , help='Either file name with e-mail message\n' + \
                                 'Or the message itself'
                          )
                          
      self.cp.add_argument( '-q'
                          , '--quantity'
                          , type=int
                          , default=1
                          , dest='message_quantity'
                          , help='Number of message copies to send'
                          )

      self.cp.add_argument( '-n'
                          , '--at-a-time'
                          , type=int
                          , dest='misc_at_a_time'
                          , help='Number of messages to send in one connection'
                          )
      self.cp.add_argument( '-z'
                          , '--rand-content'
                          , action='store_true'
                          , default=False
                          , dest='misc_rand_content'
                          , help='Whether to add random content to each message'
                          )
                          
      return self.cp.parse_args()

  def getMessage(self):
    '''
    Takes available attributes and constructs
    a mailer.Message object

    Return new mailer.Message object
    '''
    msg = mailer.Message()
    msg.From = self.getFrom()
    msg.To = self.getInfoPrompt('message_to')
    msg.CC = self.getInfo('message_cc')
    msg.BCC = self.getInfo('message_bcc')
    msg.Subject = self.message_subject
    msg.Body = self.getBody()
    msg.Html = self.message_html
    msg.Date = self.message_date
    msg.attachments = self.message_attachments

    return msg

  def getFrom(self):
    '''
    Return the From field for the e-mail.

    Defaults to the SMTP username if no
    explicit From header is provided.
    '''
    return self.message_from if self.message_from \
                             else self.smtp_username

  def getInfo(self, name):
    '''
    Returns a particular piece of information
    required for sending a message.

    name holds the attribute name that we want
    to get data for.

    If no attribute value is provided on the command
    line or in a config file it defaults to None.
    '''
    if not getattr(self, name):
      setattr(self, name, None)

    return getattr(self, name)

  def getInfoPrompt(self, name, silent=False):
    if not getattr(self, name):
      section = name.split('_')[0]
      value = ' '.join(name.split('_')[1:])
      prompt = '{} {}> '.format(section.upper(), value.upper())

      if silent:
        info = gp(prompt)
      else:
        info = raw_input(prompt)

      setattr(self, name, info)

    return getattr(self, name)

  def getBody(self):
    '''
    Save and return the message body.
    '''
    # See if a body was specified previously
    if self.message_body:
      if os.path.isfile(self.message_body):
        return open(self.message_body).read()
      else:
        return self.message_body

    # Otherwise, read from stdin until EOF
    print 'Enter message body (Ctrl+D when done)> ' 
    body = sys.stdin.readlines()
    self.message_body = '\n'.join(body)
    return self.message_body

  def getMailer(self):
    '''
    Creater a mailer.Mailer object and return it
    to the caller.
    '''
    host = self.smtp_server
    port = self.smtp_port
    tls = self.smtp_tls
    usr = self.getInfoPrompt('smtp_username')
    pwd = self.getInfoPrompt('smtp_password', silent=True)
    mail = mailer.Mailer(host=host, port=port, 
                          use_tls=tls, usr=usr, pwd=pwd)
    print '[+] Logging in as', usr, 'to', \
                              '{}:{}'.format(host, port)
    mail.login(usr, pwd)
    return mail

  def send(self, at_a_time=None):
      '''
      Send the specified quantity of e-mail messages
      '''
      # Get all required variables ready to rock
      num_errors = 0
      max_errors = 6 
      error_delay = 2.0 
      delay = 0.33
      num = self.message_quantity
      width = len(str(num))
      at_a_time = self.misc_at_a_time

      mail = self.getMailer()

      while True:
        try:
          # Get the messages ready
          msgs = []
          for n in range(num):
            msgs.append(self.getMessage())
          
          if self.misc_rand_content:
            for n in range(num):
              msgs[n].Body += rand_string()

          # Send them all at once if at_a_time is None
          # or at_a_time is greater than quantity
          if not at_a_time or at_a_time > num:
            print '[+] Sending {} messages'.format(num)
            mail.send(msgs)

          else:
            # Send certain amount at a time
            for n in range(0, num, at_a_time):
              mail.send(msgs[n : n + at_a_time])
              num_sent = len(msgs[n : n + at_a_time])
              print '[Sent]: {:{}} message{}'.format(\
                      num_sent, width, 's' if num_sent > 1 else '')
              time.sleep(delay)

          # break after sending messages
          break
        except KeyboardInterrupt:
          sys.exit('Done!')
        except:
          # When an error occurs, print its message
          # Then see if too many have occurred
          # Otherwise, wait error_delay**num_errors secs
          sys.stderr.write('[Error]: {}\n'.format(sys.exc_info()[0]))

          num_errors += 1
          if num_errors > max_errors:
            sys.exit('Too many errors from the SMTP server')
          
          sys.stderr.write('[Sleep]: For {} secs'.format(\
                                    error_delay**num_errors))
          time.sleep(error_delay**num_errors)
            
if __name__ == '__main__':
    mm = MassMailer()
    mm.send()

    save = raw_input('Do you want to save ' + \
                     'your data to a config file? (y/n) ')
    if save.lower() == 'y':
      save_fn = raw_input('Enter desired config file name> ')
      save_pw = raw_input('Save password, too? (y/n) ')
      save_pw = True if save_pw.lower() == 'y' else False
      mm.saveConfigFile(save_fn, save_pw)   
