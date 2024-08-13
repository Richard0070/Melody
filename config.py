import os
import discord
import yaml

with open('dashboard.yaml', 'r') as yamlfile:
    config = yaml.safe_load(yamlfile)
    role_levels = config.get('role_levels', {})
staff_role_ids = list(role_levels.keys())

def is_staff(ctx):
    user_role_ids = [role.id for role in ctx.author.roles]
    return any(role_id in staff_role_ids for role_id in user_role_ids)
  
TOKEN = os.environ['TOKEN']
MONGO = os.environ['MONGO']

SUCCESS = "<:zep_check:1237231842470527088>"
SETUP = "<:setup:1255996513776304291>"
DELETE = "<:delete:1244686471282163754>"
MESSAGE = "<:message:1244858435736965172>"
CHANNEL = "<:channel:1244644991649714257>"
MENTION = "<:Mention:1244710139416543233>"
REPLY = "<:reply:1244650731869306931>"
CLOSE = "<:close:1249420284679688283>"
FILL = "<:fill_app:1249437776663937125>"
ERROR = "<:error:1249582431493947494>"
QUESTION = "<:ques:1249593164059119631>"
STOP = "<:stop:1255379601220173875>"
FILE = "<:datafile:1256013379018035341>"
LATENCY = "<:latency:1256486149258612778>"
CPU = "<:cpu:1256486270453153897>"
MEMORY = "<:Memory:1256486346357477467>"
SYSTEM = "<:system:1256486459234582559>"
PYTHON = "<:python:1256486670929367132>"
STAFF = "<:staff:1265694118542311444>"
TOWN = "<:clan:1266058096438935714>"
VIEW = "<:view:1268943567787917385>"