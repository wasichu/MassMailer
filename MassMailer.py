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
import traceback
import urllib2

# External library imports
for ext_lib in ('mailer', 'requests'):
  try:
    exec 'import {}'.format(ext_lib)
  except ImportError:
    sys.exit('Install the {lib} library: pip install {lib}'.\
        format(lib=ext_lib))

def is_float_str(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
      
def is_list_str(s):
  if '[' in s and ']' in s:
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

def text_gen(text_loc, num_chars):
  '''
  Generator yielding num_chars at a time
  from either a text file or a URL as 
  passed into text_loc.
  '''
  # See if it's a local file or a URL
  if os.path.isfile(text_loc):
    with open(text_loc) as f:
      while True:
        text = f.read(num_chars)
        if not text:
          break
        yield text
  else: 
    r = requests.get(text_loc, stream=True)
    for text in r.iter_content(chunk_size=num_chars):
      if text:
        yield text

def rand_string(alphabet=printable, len_min=1, len_max=6):
  length = random.randint(len_min, len_max)
  s = ''
  for n in range(length):
    s += random.choice(alphabet)
  return s

def rand_words(words, num_words=4):
  return [random.choice(words) for n in range(num_words)]

class MassMailer(object):
  # Seed PRNG at class creation
  random.seed()

  def __init__(self):
    '''
    MassMailer constructor.
    
    Takes a path to a config file compatible with
    Python's ConfigParser standard library module.
    Defaults to a .conf file named after this class
    in the same directory as this module.
    '''
    # Parse command line args
    self.parseArgs()

    # If necessary, parse the config file
    if self.config and os.path.isfile(self.config):
        self.cp = cp()
        self.cp.read(self.config)
    
        # Parse the config file
        self.parseConfig()
    
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
        elif v.lower() == 'true' or v.lower() == 'false':
          v = True if v.lower() == 'true' else False    
        elif v and all(map(str.isdigit, v)):
          v = int(v)
        elif v and is_float_str(v):
          v = float(v)
        elif v and is_list_str(v):
          v = list(v)
          print 'list: v'
        
        # If no command line argument, then use config 
        if not getattr(self, '_'.join((section, opt))):
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

          # Don't want the string "None" saved
          if val is None:
            val = ''

          # Special handling of the password
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
          formatter_class=ap.RawTextHelpFormatter)
      
      # Config file
      self.cp.add_argument( '--config'
                          , help='Path to config file'
                          )

      # SMTP options
      self.cp.add_argument( '-s'
                          , '--server'
                          , help='SMTP server\'s hostname'
                          , dest='smtp_server'
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
                          )
      self.cp.add_argument( '-w'
                          , '--password'
                          , dest='smtp_password'
                          , help='SMTP password'
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

      # Misc Options
      self.cp.add_argument( '-x'
                          , '--quiet'
                          , action='store_true'
                          , dest='misc_quiet'
                          , help='Turns off prompt to save options'
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
      self.cp.add_argument( '--bible-quote'
                          , action='store_true'
                          , default=False
                          , dest='misc_bible_quote'
                          , help='Include random bible quote in each message'
                          )
      self.cp.add_argument( '--fortune'
                          , action='store_true'
                          , default=False
                          , dest='misc_fortune'
                          , help='Include random UNIX fortune in each message'
                          )
      self.cp.add_argument( '--chuck-norris'
                          , action='store_true'
                          , default=False
                          , dest='misc_chuck_norris'
                          , help='Include random Chuck Norris joke in each message'
                          )
      self.cp.add_argument( '--text'
                          , dest='misc_text_location'
                          , help='Filename or URL of text to send.\n' + \
                                 'No other message content will be\n' + \
                                 'sent if this option is included.'
                          )
      self.cp.add_argument( '--chars-per-msg'
                          , dest='misc_chars_per_msg'
                          , type=int
                          , default=160
                          , help='Only used in conjunction with --text.\n' + \
                                 'Specifies the number of characters per\n' + \
                                 'message to send from the text.'
                          )
      self.cp.add_argument( '--send-all-text'
                          , dest='misc_send_all_text'
                          , action='store_true'
                          , help='Only used in conjunction with --text.\n' + \
                                 'Whether to send all of the text or just\n' + \
                                 'the quantity specified in -q/--quantity.'
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
    if (not hasattr(self, name)) or (not getattr(self, name)):
      setattr(self, name, None)

    return getattr(self, name)

  def getInfoPrompt(self, name, silent=False):
    if not getattr(self, name):
      section = name.split('_')[0]
      value = ' '.join(name.split('_')[1:])
      prompt = '{} {}> '.format(section.upper(), value.title())

      if silent:
        info = gp(prompt)
      else:
        info = raw_input(prompt)

      setattr(self, name, info)

    return getattr(self, name)

  def getQuantity(self):
    if self.misc_text_location and self.misc_send_all_text:
      self.message_quantity = sys.maxint
    return self.message_quantity

  def getBody(self):
    '''
    Save and return the message body.
    '''
    # See if we need to send part of a text file
    if self.misc_text_location:
      if not hasattr(self, 'text_gen'):
        self.text_gen = text_gen(self.misc_text_location, 
                                    self.misc_chars_per_msg)
      return next(self.text_gen)

    # Get the base of the message body
    if not self.message_body:
      self.getBodyBase()

    # Start with a base for the body
    body = self.message_body

    # Check if we need random content
    if self.misc_rand_content:
      if not getattr(self, 'words'):
        self.words = [word.strip() for word in open('cracklib-small')]
      rws = ' '.join(rand_words(words))
      body += '\n' + rws.capitalize() + '.'

    # See if we also want a bible quote
    if self.misc_bible_quote:
      bible_url = 'http://labs.bible.org/api/?passage=random'
      bible_url += '&formatting=plain'
      response = urllib2.urlopen(bible_url)
      bible_quote = response.read()
      body += '\n' + bible_quote 

    # How about a fortune
    if self.misc_fortune:
      fortune_url = 'http://www.iheartquotes.com/api/v1/random'
      response = urllib2.urlopen(fortune_url)
      fortune = response.read()
      body += '\n' + fortune

    # How about some Chuck Norris
    if self.misc_chuck_norris:
      norris_url = 'http://api.icndb.com/jokes/random'
      response = urllib2.urlopen(norris_url)
      norris = json.loads(response.read())['value']['joke']
      body += '\n' + norris

    return body

  def getBodyBase(self):
    '''
    Save and return the basic message body
    which will be included on the command
    line or typed on stdin.
    '''
    # See if a body was specified previously
    if self.message_body is not None:
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
    host = self.getInfoPrompt('smtp_server')
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
      delay = self.misc_delay if hasattr(self, 'misc_delay') else 0.33
      num = self.getQuantity()
      width = len(str(num))
      at_a_time = self.misc_at_a_time
      at_a_time = abs(at_a_time) if type(at_a_time) == int else at_a_time

      mail = self.getMailer()

      while True:
        try:
          # Get the messages ready
          msgs = []
          try:
            for n in range(num):
              msgs.append(self.getMessage())
          except StopIteration:
            pass
          
          # Send them all at once if at_a_time is None
          # or at_a_time is greater than quantity
          if not at_a_time or at_a_time > num:
            print '[+] Sending {} message{}'.format(num,
                                      's' if num > 1 else '')
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
          sys.stderr.write('[Error]: {}\n'.format(sys.exc_info()[0]))
          traceback.print_tb(sys.exc_info()[2])
          sys.exit('Failure.')
          
            
if __name__ == '__main__':
    mm = MassMailer()
    mm.send()

    if not mm.misc_quiet:
      save = raw_input('Do you want to save ' + \
                       'your options to a config file? (y/n) ')
      if save.lower() == 'y':
        save_fn = raw_input('Enter desired config file name> ')
        save_pw = raw_input('Save password, too? (y/n) ')
        save_pw = True if save_pw.lower() == 'y' else False
        mm.saveConfigFile(save_fn, save_pw)   
