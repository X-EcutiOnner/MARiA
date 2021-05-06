# -*- coding: utf-8 -*-

import wx
import threading
import binascii
import time
import datetime
import socket
import traceback
from scapy.all import *

import const

MARiA_MAJOR_VERSION = 0
MARiA_MINOR_VERSION = 0
MARiA_MAJOR_REVISION = 29
MARiA_VERSION = "v{}.{}.{}".format(MARiA_MAJOR_VERSION, MARiA_MINOR_VERSION, MARiA_MAJOR_REVISION)

Configuration = {"Window_XPos": 0, "Window_YPos": 0, "Width": 800, "Height": 500, "Show_OtherPacket": 1}
IP_Target = {"IP": "127.0.0.1"}
dummy_mob = ["unknown.gat",0,0,"No Mob Name",0,0,0]
dummy_npc = ["unknown.gat",0,0,0,"No NPC Name",0,0]
dummy_chr = {'Char_id': 0, 'Char_Name': 0, "BaseExp": -1, "JobExp": -1, "Zeny": -1}
dummy_inv = {'Nameid': 0, 'Amount': 0}
Packetlen = {}
IgnorePacket = {}
chrselect = []
chrselect = dummy_chr
chrdata = {"aid": 0, "name": "unknown name", "mapname": "unknown.gat", "x": 0, "y": 0, "BaseExp": -1, "JobExp": -1, "Zeny": -1}
mobdata = {}
mobdata.setdefault('5121',{})
mobdata['5121'].setdefault(0,{})
mobdata['5121'][0] = dummy_mob
npcdata = {}
npcdata.setdefault('5121',{})
npcdata['5121'].setdefault(0,{})
npcdata['5121'][0] = dummy_npc
warpnpc = {}
warpnpc.setdefault('5121',{})
warpnpc['5121'].setdefault(0,{})
warpnpc['5121'][0] = "dummy"
inventory = {}
inventory.setdefault('item',{})
inventory['item'].setdefault(0,{})
inventory['item'][0] = dummy_inv
waitingroom = {}

TargetIP = 0
IgnorePacketAll = 0

MAX_PACKET_DB = 0x0b90

SkillName = const.SKILLNAME
EFST = const.EFST
NPC = const.NPC
MOB = const.MOB
RANDOPT = const.RANDOPT

RFIFOS = lambda p, pos1, pos2: p[pos1*2:pos2*2]
RFIFOB = lambda p, pos: int(p[pos*2:pos*2+2],16)
RFIFOW = lambda p, pos: int(p[pos*2+2:pos*2+4]+p[pos*2:pos*2+2],16)
RFIFOL = lambda p, pos: int(p[pos*2+6:pos*2+8]+p[pos*2+4:pos*2+6]+p[pos*2+2:pos*2+4]+p[pos*2:pos*2+2],16)
RFIFOQ = lambda p, pos: int(p[pos*2+14:pos*2+16]+p[pos*2+12:pos*2+14]+p[pos*2+10:pos*2+12]+p[pos*2+8:pos*2+10]+p[pos*2+6:pos*2+8]+p[pos*2+4:pos*2+6]+p[pos*2+2:pos*2+4]+p[pos*2:pos*2+2],16)
RFIFOPOSX = lambda p, pos: (int(p[pos*2:pos*2+2],16)<<2) + ((int(p[pos*2+2:pos*2+4],16)&0xc0)>>6)
RFIFOPOSY = lambda p, pos: ((int(p[pos*2+2:pos*2+4],16)&0x3f)<<4) + ((int(p[pos*2+4:pos*2+6],16)&0xF0)>>4)
RFIFOPOSD = lambda p, pos: (int(p[pos*2+4:pos*2+6],16)&0xF)

gettick = lambda : time.time()
getskill = lambda n: n if not n in SkillName else SkillName[n]
getefst = lambda n: n if not n in EFST else EFST[n]
getrandopt = lambda n: n if not n in RANDOPT else RANDOPT[n]

def read_config_db():
	path = './Config.txt'

	with open(path) as f:
		for s_line in f:
			if s_line[:2] == "//":
				continue
			elif s_line[:1] == "\n":
				continue
			else:
				l = s_line.split('\t')
				if len(l) >= 2:
					if l[0] in Configuration:
						Configuration[str(l[0])] = int(l[1])

def read_ip_db():
	path = './IP_Target.txt'

	with open(path) as f:
		for s_line in f:
			if s_line[:2] == "//":
				continue
			elif s_line[:1] == "\n":
				continue
			else:
				l = s_line.split('\t')
				if len(l) >= 2:
					if l[0] in IP_Target:
						IP_Target[str(l[0])] = str(l[1])

def read_packet_db():
	path = './PacketLength.txt'

	with open(path) as f:
		for s_line in f:
			if s_line[:2] == "//":
				continue
			elif s_line[:1] == "\n":
				continue
			else:
				l = s_line.split(' ')
				if len(l) >= 2:
					Packetlen[int(l[0],16)] = int(l[1])
				else:
					l = s_line.split(',')
					if len(l) >= 2:
						Packetlen[int(l[0],16)] = int(l[1])

def read_ignore_db():
	path = './Ignore.txt'

	with open(path) as f:
		for s_line in f:
			if s_line[:2] == "//":
				continue
			elif s_line[:1] == "\n":
				continue
			else:
				l = s_line.split(' ')
				if len(l) >= 2:
					if int(l[0],16) == 0xffff:
						global IgnorePacketAll
						IgnorePacketAll = int(l[1])
					else:
						IgnorePacket[int(l[0],16)] = int(l[1])

def save_configuration():
	path = './Config.txt'

	savedata = []
	with open(path) as f:
		for s_line in f:
			if s_line[:2] == "//":
				savedata.append(s_line)
			elif s_line[:1] == "\n" or not s_line:
				savedata.append("\n")
			else:
				sp = s_line.split('\t')
				if len(sp) >= 2:
					if sp[0] in Configuration:
						sp[1] = str(Configuration[sp[0]])
				sp2 = '\t'.join(sp)
				savedata.append(sp2)
	s_lines = ['' if '\n' in s else s for s in savedata]
	sp = '\n'.join(s_lines)
	with open(path, mode="w") as f:
		f.write(sp)

class MARiA_Catch(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.data = []
		self.data.append("")
		self.datacnt = 0
		self.charport = 6121
		self.mapport = 5121
		self.pause_flag = True

	def readpause(self):
		return self.pause_flag

	def readdata(self,dpos):
		if len(self.data) > 1:
			return self.data[dpos+1]
		else:
			return ""

	def setdata(self):
		self.data = []
		self.data.append("")
		self.datacnt = 0

	def readcnt(self):
		return self.datacnt

	def setport(self, num1, num2):
		self.charport = num1
		self.mapport = num2

	def run(self):
		sniff (filter = "ip host "+TargetIP, prn=self.OnCatch, count=0)

	def c_pause(self,flag):
		self.pause_flag = flag

	def is_this_target_packet(self, packet):
		return TCP in packet and (packet[TCP].sport == self.charport or packet[TCP].sport == self.mapport)

	def OnHexEx(self,x):
		s = ""
		x = bytes_encode(x)
		x_len = len(x)
		i = 0
		while i < x_len:
			for j in range(16):
				if i + j < x_len:
					s += "%02x" % orb(x[i + j])
			i += 16
		return s

	def OnCatch(self, packet):
		if self.pause_flag == False:
			if self.is_this_target_packet(packet) == True:
				if Raw in packet:
					raw = packet.lastlayer()
					self.data.append(self.OnHexEx(raw))
					self.datacnt += 1
		else:
			pass

class MARiA_Frame(wx.Frame):
	Started		= False
	Speed		= 25
	ID_TIMER	= 1
	buf			= ""
	bufcnt		= 0
	prev_num	= 0
	logout_mode	= 0
	tmp_id		= 0
	timerlock	= 0
	timerlockcnt= 0
	packet_lasttick = 0
	th = MARiA_Catch()
	th.setDaemon(True)

	def __init__(self, parent, id, title):
		wx.Frame.__init__(
			self, 
			parent, 
			id,
			title=title, 
			pos=(Configuration['Window_XPos'],Configuration['Window_YPos']),
			size=(Configuration['Width'],Configuration['Height']))

		self.timer = wx.Timer(self, MARiA_Frame.ID_TIMER)

		sb = self.CreateStatusBar()
		sb.SetFieldsCount(4)
		sb.SetStatusWidths([150, 130, 130, 120])
		sb.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
		sb.SetStatusText('BaseExp: '+str(chrdata['BaseExp']), 1)
		sb.SetStatusText('JobExp: '+str(chrdata['JobExp']), 2)
		sb.SetStatusText('Zeny: '+str(chrdata['Zeny']), 3)
		self.statusbar = sb

		menubar = wx.MenuBar()
		file = wx.Menu()
		edit = wx.Menu()

		copybinary = file.Append(-1, "Copy Binary")
		#copyscript = file.Append(-1, "Copy Log")
		savelogfile = file.Append(-1, "Save Log")
		self.Bind(wx.EVT_MENU, self.OnSaveLogFile, savelogfile)

		file.AppendSeparator()
		item_1 = wx.MenuItem(file, -1, 'Auriga', kind=wx.ITEM_RADIO)
		item_2 = wx.MenuItem(file, -1, 'rAthena', kind=wx.ITEM_RADIO)
		item_3 = wx.MenuItem(file, -1, 'Hercules', kind=wx.ITEM_RADIO)
		self.scripttimer = wx.MenuItem(file, -1, 'Show Log Timer', kind=wx.ITEM_CHECK)
		file.Append(item_1)
		file.Append(item_2)
		file.Append(item_3)
		file.AppendSeparator()
		file.Append(self.scripttimer)

		reloadignore = edit.Append(-1, "Reload IgnorePacket")
		self.Bind(wx.EVT_MENU, self.OnReloadIgnore, reloadignore)

		reloadpacket = edit.Append(-1, "Reload PacketLength")
		self.Bind(wx.EVT_MENU, self.OnReloadPacket, reloadpacket)

		edit.AppendSeparator()

		clearcache = edit.Append(-1, "Clear Cache")
		self.Bind(wx.EVT_MENU, self.OnClearCache, clearcache)

		clearbinary = edit.Append(-1, "Clear Binary")
		self.Bind(wx.EVT_MENU, self.OnClearBinary, clearbinary)

		clearscript = edit.Append(-1, "Clear Log Window")
		self.Bind(wx.EVT_MENU, self.OnClearScript, clearscript)

		edit.AppendSeparator()

		moblist = edit.Append(-1, "Monster Info")
		self.Bind(wx.EVT_MENU, self.OnMonsterList, moblist)

		menubar.Append(file, '&File')
		menubar.Append(edit, '&Edit')
		self.SetMenuBar(menubar)

		sp = wx.SplitterWindow(self,-1, style=wx.SP_LIVE_UPDATE)

		vbox = wx.BoxSizer(wx.VERTICAL)
		p1 = wx.Panel(sp, -1)

		hbox1 = wx.BoxSizer(wx.HORIZONTAL)
		st3 = wx.StaticText(p1, -1, '  Char Port : ')
		hbox1.Add(st3, 0, wx.LEFT | wx.BOTTOM | wx.TOP, 2)
		self.charport = wx.TextCtrl(
			p1,
			-1,
			size=(40,10))
		self.charport.WriteText('6121')
		hbox1.Add(self.charport, 1, wx.EXPAND)

		st1 = wx.StaticText(p1, -1, '  Map Port : ')
		hbox1.Add(st1, 0, wx.LEFT | wx.BOTTOM | wx.TOP, 2)
		self.mapport = wx.TextCtrl(
			p1,
			-1,
			size=(40,10))
		self.mapport.WriteText('5121')
		hbox1.Add(self.mapport, 1, wx.EXPAND)

		st2 = wx.StaticText(p1, -1, '  Action : ')
		hbox1.Add(st2, 1, wx.RIGHT | wx.BOTTOM | wx.TOP, 2)
		self.button = wx.Button(
			p1,
			-1,
			'Start',
			size=(20,20))
		hbox1.Add(self.button,3)
		vbox.Add(hbox1, 0, wx.LEFT | wx.RIGHT | wx.TOP, 2)

		self.btext = wx.TextCtrl(
			p1,
			-1,
			style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
		vbox.Add(self.btext, 1, wx.EXPAND)

		vbox2 = wx.BoxSizer(wx.VERTICAL)
		p2 = wx.Panel(sp, style=wx.SUNKEN_BORDER)
		self.text = wx.TextCtrl(
			p2,
			-1,
			style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL)
		vbox2.Add(self.text, 1, wx.EXPAND)

		sp.SplitHorizontally(p1, p2)
		sp.SetMinimumPaneSize(110)
		self.button.Bind(wx.EVT_BUTTON, self.OnStart)
		self.Bind(wx.EVT_TIMER, self.OnTimer, id=MARiA_Frame.ID_TIMER)

		self.Bind(wx.EVT_CLOSE, self.OnClose)

		icon = wx.Icon(r"./icon.ico", wx.BITMAP_TYPE_ICO)
		self.SetIcon(icon)

		self.text.AppendText("setup...\n")

		global TargetIP
		TargetIP = socket.gethostbyname(IP_Target["IP"])
		self.text.AppendText("Target IP : " + TargetIP + "\n")

		p1.SetSizer(vbox)
		p2.SetSizer(vbox2)
		self.Show(True)

	def OnStart(self, event):
		if self.Started == False:
			self.th.start()
			self.Started = True
		if self.th.readpause() == True:
			self.text.AppendText("MARiA : Started...\n")
			self.th.setport(int(self.charport.GetValue()), int(self.mapport.GetValue()))
			self.th.c_pause(False)
			self.timer.Start(MARiA_Frame.Speed)
			self.button.SetLabel("Stop")
			self.charport.Disable()
			self.mapport.Disable()
		else:
			self.th.c_pause(True)
			self.timer.Stop()
			self.button.SetLabel("Start")
			self.charport.Enable()
			self.mapport.Enable()

	def OnTimer(self, event):
		if event.GetId() == MARiA_Frame.ID_TIMER:
			if self.timerlock == 0:
				self.timerlockcnt = 0
				data = self.th.readdata(self.bufcnt)
				if data != "":
					self.bufcnt += 1
					self.buf += data
					self.GetPacket()
					if self.bufcnt == self.th.readcnt():
						self.th.setdata()
						self.bufcnt = 0
			else:
				#ロックされてるときはカウンタをあげる
				self.timerlockcnt += 1
				if self.timerlockcnt >= 20:	#デッドロックの予感
					self.timerlock		= 0
					self.timerlockcnt	= 0
					self.buf = ""
					print("DeadLock buf Clear\n")
		else:
			event.Skip()
	def OnClose(self, event):
		pos = self.GetScreenPosition()
		size = self.GetSize()
		Configuration["Window_XPos"] = pos[0]
		Configuration["Window_YPos"] = pos[1]
		Configuration["Width"] = size[0]
		Configuration["Height"] = size[1]
		save_configuration()
		event.Skip()

	def OnSaveLogFile(self, event):
		text = self.text.GetValue()
		file = open(("log.txt"), "w")
		file.write(text)
		file.close()
		wx.MessageBox('Log file has been save to "Log.txt"', 'Save Log File', wx.OK | wx.ICON_INFORMATION)

	def OnReloadPacket(self, event):
		global Packetlen
		Packetlen.clear()
		Packetlen = {}
		read_packet_db()
		self.text.AppendText("@reload packetlength done.\n")

	def OnReloadIgnore(self, event):
		global IgnorePacket
		global IgnorePacketAll
		IgnorePacket.clear()
		IgnorePacket = {}
		IgnorePacketAll = 0
		read_ignore_db()
		self.text.AppendText("@reload ignorepacket done.\n")

	def OnClearCache(self, event):
		global chrdata
		chrdata.clear()
		chrdata = {"aid": 0, "name": "unknown name", "mapname": "unknown.gat", "x": 0, "y": 0, "BaseExp": 0, "JobExp": 0, "Zeny": 0}
		global mobdata
		mobdata.clear()
		mobdata = {}
		mobdata.setdefault('5121',{})
		mobdata['5121'].setdefault(0,{})
		mobdata['5121'][0] = dummy_mob
		global npcdata
		npcdata.clear()
		npcdata = {}
		npcdata.setdefault('5121',{})
		npcdata['5121'].setdefault(0,{})
		npcdata['5121'][0] = dummy_npc
		global warpnpc
		warpnpc.clear()
		warpnpc = {}
		warpnpc.setdefault('5121',{})
		warpnpc['5121'].setdefault(0,{})
		warpnpc['5121'][0] = "dummy"

	def OnClearBinary(self, event):
		self.btext.Clear()

	def OnClearScript(self, event):
		self.text.Clear()

	def OnMonsterList(self, event):
		mapmobs = {}
		mapmobs.setdefault('unknown.gat',{})
		mapmobs['unknown.gat'].setdefault('0',{})
		mapmobs['unknown.gat']['0'] = ["unknown name", 0]
		for p in mobdata.keys():
			for aid in mobdata[p].keys():
				if aid > 0:
					#if mapmobs[mobdata[p][aid][MOB.MAP]][mobdata[p][aid][MOB.CLASS]][1]:
						#mapmobs[map][class_][2] += 1
					#else:
					#mapmobs[mobdata[p][aid][MOB.MAP]][mobdata[p][aid][MOB.CLASS]] = [mobdata[p][aid][MOB.NAME], 1]
					if mobdata[p][aid][MOB.MAP] in mapmobs:
						if mobdata[p][aid][MOB.CLASS] in mapmobs[mobdata[p][aid][MOB.MAP]]:
							mapmobs[mobdata[p][aid][MOB.MAP]][mobdata[p][aid][MOB.CLASS]][1] += 1
						else:
							mapmobs[mobdata[p][aid][MOB.MAP]][mobdata[p][aid][MOB.CLASS]] = [ mobdata[p][aid][MOB.NAME],1 ]
					else:
						mapmobs[mobdata[p][aid][MOB.MAP]] = { mobdata[p][aid][MOB.CLASS]: [ mobdata[p][aid][MOB.NAME],1 ] }
		for map in mapmobs.keys():
			self.text.AppendText("//------------------------------------------------------------\n")
			self.text.AppendText("// {}\n".format(map))
			for class_ in mapmobs[map].keys():
				if class_ != '0':
					self.text.AppendText("{},0,0,0,0\tmonster\t{}\t{},{},0,0,0\n".format(map,mapmobs[map][class_][0],class_,mapmobs[map][class_][1]))

	def CheckNearNPC(self, m, x, y):
		p = self.mapport.GetValue()
		if p in npcdata.keys():
			for aid in npcdata[p].keys():
				nm = npcdata[p][aid][NPC.MAP]
				class_ = npcdata[p][aid][NPC.CLASS]
				if nm == m and class_ == 45:
					nx = npcdata[p][aid][NPC.POSX]
					ny = npcdata[p][aid][NPC.POSY]
					if nx+2 >= x and nx-2 <= x and ny+2 >= y and ny-2 <= y:
						return aid
		return -1

	def GetPacket(self):
		buf = self.buf
		tick = gettick()
		self.timerlock = 1
		while not buf == "":
			lasttick = gettick()
			if lasttick - tick > 50:	#50msを超えたら再帰
				break
			total_len = len(buf)
			if total_len < 4:	#4文字以下なら
				break
			num = RFIFOW(buf,0)
			if num in Packetlen.keys():
				packet_len = Packetlen[num]
			else:
				if num > MAX_PACKET_DB:
					snum = RFIFOW(buf,1)
					if snum in Packetlen.keys():
						print("[Info] unknown 1 byte skiped, result:",format(snum, '#06x'),", prev:",format(self.prev_num, '#06x'),", skiped byte: 0x",buf[:2],"\n")
						num = snum
						packet_len = Packetlen[num]
						buf = buf[2:total_len]	#1byte skip
					else:
						print("[Error] unknown ultra high packet, id: ",format(num, '#06x'),", prev:",format(self.prev_num, '#06x'),", clear buf: ",buf,"\n")
						self.btext.AppendText("\nultrahigh_packetid_" + format(num, '#06x')+", prev:"+format(self.prev_num, '#06x'))
						self.text.AppendText("//------------------------------------------------------------\n")
						self.text.AppendText(buf + "\n")
						self.text.AppendText("//------------------------------------------------------------\n")
						self.buf = buf = ''
						break
				else:
					snum = RFIFOW(buf,1)
					if snum in Packetlen.keys():
						print("[Info] unknown 1 byte skiped, result:",format(snum, '#06x'),", prev:",format(self.prev_num, '#06x'),", skiped byte: 0x",buf[:2],"\n")
						num = snum
						packet_len = Packetlen[num]
						buf = buf[2:total_len]	#1byte skip
					else:
						print("[Error] unknown packet len: ",format(num, '#06x'),", prev:",format(self.prev_num, '#06x'),", set packet_len: 2\n")
						self.btext.AppendText("\nunknown_packetlength" + format(num, '#06x')+", prev:"+format(self.prev_num, '#06x'))
						packet_len = 2
			if packet_len == -1:
				packet_len = RFIFOW(buf,2)
				if packet_len <= 0:
					print("[Error] unknown packet len = 0: ",format(num, '#06x'),", prev:",format(self.prev_num, '#06x'),", clear buf: ",buf,"\n")
					self.btext.AppendText("\n"+format(num, '#06x')+" len=0: Please check PacketLength.txt. (prev:" + format(self.prev_num, '#06x')+")\n")
					self.buf = buf = ''
					break
			if packet_len*2 > total_len:	#パケット足りてない
				if self.packet_lasttick > 0 and lasttick - self.packet_lasttick > 1000:	#1000ms待機しても続きが来ない
					print("[Error] packet time out, target:",format(num, '#06x'),", len: ",str(packet_len),", prev:",format(self.prev_num, '#06x'),", clear buf: ",buf,"\n")
					self.btext.AppendText("\n" + format(num, '#06x')+"(len = "+str(packet_len)+") Time out. Please check PacketLength.txt. (prev:" +format(self.prev_num, '#06x')+ ")")
					self.buf = buf = ''
					self.packet_lasttick = 0
				elif self.packet_lasttick == 0:
					self.packet_lasttick = tick
				break
			if self.logout_mode >= 1:
				if buf[:4] == "0000":
					if total_len >= 10:
						if buf[:10] == "0000000000":
							if packet_len*2+10 < total_len:
								self.buf = buf = buf[10:total_len]
							else:
								self.buf = buf = ''
						else:
							self.logout_mode = 0
					break
				else:
					self.logout_mode = 0
			if num == 0x229:
				if total_len >= packet_len*2+10:
					if buf[packet_len*2:packet_len*2+10] == "0000000000":
						packet_len += 5
				else:
					self.logout_mode = 1
			ignore_type = 0
			if num in IgnorePacket.keys():
				ignore_type = IgnorePacket[num]
			if (ignore_type&1 == 0 and IgnorePacketAll&1 == 0) or ignore_type&4:
				i = 0
				if self.btext.GetValue() != '':
					self.btext.AppendText('\n')
				self.btext.AppendText(format(num, '#06x')+": ")
				while i < packet_len*2:
					self.btext.AppendText(buf[i:i+2]+ ' ')
					i += 2
			if (ignore_type&2 == 0 and IgnorePacketAll&2 == 0) or ignore_type&8:
				try:
					if packet_len >= 2:
						self.ReadPacket(num, packet_len)
				except Exception as e:
					print(traceback.format_exc())
					self.buf = buf = ''
					break
			self.prev_num = num
			if packet_len*2 < total_len:
				self.buf = buf = buf[packet_len*2:total_len]
			else:
				self.buf = buf = ''
		self.timerlock = 0

	def ReadPacket(self, num, p_len):
		n = hex(num)
		buf = self.buf[0:p_len*2]
		if num == 0x9fe:	#spawn
			if p_len > 83:
				type	= RFIFOB(buf,4)
				aid		= RFIFOL(buf,5)
				speed	= RFIFOW(buf,13)
				option	= RFIFOL(buf,19)
				view	= RFIFOW(buf,23)
				x		= RFIFOPOSX(buf,63)
				y		= RFIFOPOSY(buf,63)
				dir		= RFIFOPOSD(buf,63)
				if type==5 or type==6 or type==12:
					i = 83
					s = buf[i*2:p_len*2]
					opt = ""
					if option == 2:
						opt = "(hide)"
					elif option == 4:
						opt = "(cloaking)"
					s_len = len(s)
					if s_len > 46 and ((s[-2:] >= '80' and s[-2:] <= '9f') or (s[-2:] >= 'e0' and s[-2:] <= '9e')):
						s = s[:-2]
					s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
					s = "" if s[0] == '\0' else s
					p = self.mapport.GetValue()
					m = chrdata['mapname']
					if type == 5:
						if p in mobdata.keys():
							if aid in mobdata[p].keys():
								pass
							else:
								cflag = 0
								if aid > 10000:
									cflag = len(self.text.GetValue())
								self.text.AppendText("@spawn(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
								mobdata[p][aid] = [m,x,y,s,view,speed,0]
								if cflag > 0:
									self.text.SetStyle(cflag, len(self.text.GetValue()), wx.TextAttr("red", "blue"))
						else:
							self.text.AppendText("@spawn(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
							mobdata[p] = { aid: [m,x,y,s,view,speed,0] }
					elif type == 6 or type==12:
						if p in npcdata.keys():
							if aid in npcdata[p].keys():
								if npcdata[p][aid][NPC.CLASS] != view:
									self.text.AppendText("@viewchange(setnpcdisplay \"{}\", {};\t// {}\n".format(s, view, aid))
								elif npcdata[p][aid][NPC.OPTION] != option:
									s2 = "@viewchange("
									if npcdata[p][aid][NPC.OPTION] == 2 or option == 2:
										s2 += "hideonnpc" if option == 2 else "hideoffnpc"
									elif npcdata[p][aid][NPC.OPTION] == 4 or option == 4:
										s2 += "cloakonnpc" if option == 4 else "cloakoffnpc"
									else:
										s2 += "hideoffnpc"
									s2 += " \""+s+"\";)\t// "+str(aid)
									npcdata[p][aid][NPC.OPTION] = option
									self.text.AppendText(s2+"\n")
							else:
								self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
								npcdata[p][aid] = [m,x,y,dir,s,view,option]
						else:
							self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
							npcdata[p] = { aid: [m,x,y,dir,s,view,option] }
		elif num == 0x9ff:	#idle
			if p_len > 84:
				type	= RFIFOB(buf,4)
				aid		= RFIFOL(buf,5)
				speed	= RFIFOW(buf,13)
				option	= RFIFOL(buf,19)
				view	= RFIFOW(buf,23)
				x		= RFIFOPOSX(buf,63)
				y		= RFIFOPOSY(buf,63)
				dir		= RFIFOPOSD(buf,63)
				if type==5 or type==6 or type==12:
					i = 84
					s = buf[i*2:p_len*2]
					opt = ""
					if option == 2:
						opt = "(hide)"
					elif option == 4:
						opt = "(cloaking)"
					s_len = len(s)
					if s_len > 46 and ((s[-2:] >= '80' and s[-2:] <= '9f') or (s[-2:] >= 'e0' and s[-2:] <= '9e')):
						s = s[:-2]
					s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
					s = "" if s[0] == '\0' else s
					p = self.mapport.GetValue()
					m = chrdata['mapname']
					if type == 5:
						if p in mobdata.keys():
							if aid in mobdata[p].keys():
								pass
							else:
								cflag = 0
								if aid > 10000:
									cflag = len(self.text.GetValue())
								self.text.AppendText("@spawn(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
								mobdata[p][aid] = [m,x,y,s,view,speed,0]
								if cflag > 0:
									self.text.SetStyle(cflag, len(self.text.GetValue()), wx.TextAttr("red", "blue"))
						else:
							self.text.AppendText("@spawn(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
							mobdata[p] = { aid: [m,x,y,s,view,speed,0] }
					elif type == 6 or type==12:
						if p in npcdata.keys():
							if aid in npcdata[p].keys():
								if npcdata[p][aid][NPC.CLASS] != view:
									self.text.AppendText("@viewchange(setnpcdisplay \"{}\", {};\t// {}\n".format(s, view, aid))
								elif npcdata[p][aid][NPC.OPTION] != option:
									s2 = "@viewchange("
									if npcdata[p][aid][NPC.OPTION] == 2 or option == 2:
										s2 += "hideonnpc" if option == 2 else "hideoffnpc"
									elif npcdata[p][aid][NPC.OPTION] == 4 or option == 4:
										s2 += "cloakonnpc" if option == 4 else "cloakoffnpc"
									else:
										s2 += "hideoffnpc"
									s2 += " \""+s+"\";)\t// "+str(aid)
									npcdata[p][aid][NPC.OPTION] = option
									self.text.AppendText(s2+"\n")
							else:
								self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
								npcdata[p][aid] = [m,x,y,dir,s,view,option]
						else:
							self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
							npcdata[p] = { aid: [m,x,y,dir,s,view,option] }
		elif num == 0x9fd:	#move
			if p_len > 90:
				type	= RFIFOB(buf,4)
				aid		= RFIFOL(buf,5)
				speed	= RFIFOW(buf,13)
				option	= RFIFOL(buf,19)
				view	= RFIFOW(buf,23)
				x		= RFIFOPOSX(buf,67)
				y		= RFIFOPOSY(buf,67)
				dir		= RFIFOPOSD(buf,67)
				if type==5 or type==6 or type==12:
					i = 90
					s = buf[i*2:p_len*2]
					opt = ""
					if option == 2:
						opt = "(hide)"
					elif option == 4:
						opt = "(cloaking)"
					s_len = len(s)
					if s_len > 46 and ((s[-2:] >= '80' and s[-2:] <= '9f') or (s[-2:] >= 'e0' and s[-2:] <= '9e')):
						s = s[:-2]
					s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
					p = self.mapport.GetValue()
					m = chrdata['mapname']
					if type == 5:
						if p in mobdata.keys():
							if aid in mobdata[p].keys():
								pass
							else:
								cflag = 0
								if aid > 10000:
									cflag = len(self.text.GetValue())
								self.text.AppendText("@move(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
								mobdata[p][aid] = [m,x,y,s,view,speed,0]
								if cflag > 0:
									self.text.SetStyle(cflag, len(self.text.GetValue()), wx.TextAttr("red", "blue"))
						else:
							self.text.AppendText("@move(type: BL_MOB, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
							mobdata[p] = { aid: [m,x,y,s,view,speed,0] }
					elif type == 6:
						if p in npcdata.keys():
							if aid in npcdata[p].keys():
								pass
							else:
								self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
								npcdata[p][aid] = [m,x,y,dir,s,view,option]
						else:
							self.text.AppendText(m+","+ str(x) + ","+ str(y) +","+ str(dir) +"\tscript\t"+ s +"\t"+ str(view) +",{/* "+ str(aid) +" "+opt+"*/}\n")
							npcdata[p] = { aid: [m,x,y,dir,s,view,option] }
					elif type == 12:
						if p in npcdata.keys():
							if aid in npcdata[p].keys():
								self.text.AppendText("@move(type: BL_WALKNPC, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
							else:
								self.text.AppendText("@move(type: BL_WALKNPC, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
								npcdata[p][aid] = [m,x,y,dir,s,view,option]
						else:
							self.text.AppendText("@move(type: BL_WALKNPC, ID: "+str(aid)+", speed: "+str(speed)+", option: "+str(hex(option))+", class: "+str(view)+", pos: (\"" +m+ "\","+str(x)+","+str(y)+"), dir: "+str(dir)+", name\""+ s +"\")\n")
							npcdata[p] = { aid: [m,x,y,dir,s,view,option] }
		elif num == 0x0b4:	#mes
			s = buf[8*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			if chrdata['name'] != 'unknown name':
				s = s.replace(chrdata['name'],"\"+strcharinfo(0)+\"")
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("mes \""+ s + "\";\n")
		elif num == 0x0b5:	#next
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("next;\n")
		elif num == 0x0b6:	#close
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("close;\n")
		elif num == 0x8d6:	#clear
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("clear;\n")
		elif num == 0x0b7:	#select
			s = buf[8*2:p_len*2-4]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			l = s.split(':')
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if len(l) == 1:
				self.text.AppendText("menu \""+s+"\",-;\n")
			elif len(l) == 2:
				self.text.AppendText("if(select(\""+s.replace(':','\",\"')+"\") == 2) {\n")
			else:
				self.text.AppendText("switch(select(\""+s.replace(':','\",\"')+"\")) {\n")
		elif num == 0x142:	#input num
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("input '@num;\n")
		elif num == 0x1d4:	#input str
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("input '@str$;\n")
		elif num == 0x1b3:	#cutin
			s = buf[2*2:p_len*2-4]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			type	= RFIFOB(buf,66)
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("cutin \""+s+"\", "+str(type)+";\n")
		elif num == 0x1b0:	#classchange
			aid		= RFIFOL(buf,2)
			type	= RFIFOB(buf,6)
			class_	= RFIFOL(buf,7)
			p		= self.mapport.GetValue()
			if p in npcdata.keys():
				if aid in npcdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("setnpcdisplay \"{}\",{};\t// {}\n".format(npcdata[p][aid][NPC.NAME], class_, aid))
					npcdata[p][aid][NPC.CLASS] = class_
			elif p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@classchange(src: \"{}\"({}), class: {}, type: {})\n".format(mobdata[p][aid][MOB.NAME],aid,class_,type))
		elif num == 0x2b3 or num == 0x9f9 or num == 0xb0c:	#quest_add
			quest_id = RFIFOL(buf,2)
			state	 = RFIFOB(buf,6)
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("setquest {};\t// state={}\n".format(quest_id, state))
		elif num == 0x2b4:	#quest_del
			quest_id = RFIFOL(buf,2)
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("delquest {};\n".format(quest_id))
		elif num == 0x09a:	#broadcast
			color		= RFIFOL(buf,4)
			s = buf[4*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			if chrdata['name'] != 'unknown name':
				s = s.replace(chrdata['name'],"\"+strcharinfo(0)+\"")
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if color == 0x65756c62:		#blue
				self.text.AppendText("announce {}, 0x10;\n".format(s))
			elif color == 0x73737373:	#ssss -> WoE
				self.text.AppendText("announce {}, 0x20;\n".format(s))
			elif color == 0x6c6f6f74:	#tool
				self.text.AppendText("announce {}, 0x30;\n".format(s))
			elif color == 0:
				self.text.AppendText("announce {}, 0;\n".format(s))
			else:
				color = format(color, '#06x')
				self.text.AppendText("@broadcast(mes: {}, type: {})\n".format(s, color))
		elif num == 0x1c3 or num == 0x40c:	#announce
			color		= RFIFOL(buf,4)
			fontType	= RFIFOW(buf,8)
			fontSize	= RFIFOW(buf,10)
			fontAlign	= RFIFOW(buf,12)
			fontY		= RFIFOW(buf,14)
			s = buf[16*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			if chrdata['name'] != 'unknown name':
				s = s.replace(chrdata['name'],"\"+strcharinfo(0)+\"")
			color = format(color, '#08x')
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if fontType == 400 and fontSize == 12 and fontAlign == 0 and fontY == 0:
				self.text.AppendText("announce \"{}\", 0x9, {};\n".format(s, color))
			else:
				fontType = format(fontType, '#06x')
				self.text.AppendText("announce \"{}\", 0x9, {}, {}, {}, {}, {};\n".format(s, color, fontType, fontSize, fontAlign, fontY))
		elif num == 0x2f0:	#progressbar
			color		= RFIFOL(buf,2)
			casttime	= RFIFOL(buf,6)
			color = format(color, '#08x')
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("progressbar {};\t//color={}\n".format(casttime,color))
		elif num == 0x1ff:	#blown
			aid	= RFIFOL(buf,2)
			x	= RFIFOW(buf,6)
			y	= RFIFOW(buf,8)
			dx	= x - chrdata['x']
			dy	= y - chrdata['y']
			dir	= 1*(dx>0  and dy<0) \
				+ 2*(dx>0  and dy==0) \
				+ 3*(dx>0  and dy>0) \
				+ 4*(dx==0 and dy>0) \
				+ 5*(dx<0  and dy>0) \
				+ 6*(dx<0  and dy==0) \
				+ 7*(dx<0  and dy<0)
			dist = abs(dx) if abs(dx) > abs(dy) else abs(dy)
			if chrdata['aid'] == aid:
				chrdata['x'] = x
				chrdata['y'] = y
				self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
				if self.scripttimer.IsChecked() == 1:
					self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
				self.text.AppendText("pushpc {}, {};\n".format(dir, dist))
		elif num == 0x08a:	#nomalattack
			type	= RFIFOB(buf,26)
			if type == 1 or type == 2 or type == 3:	#pickup/sitdown/standup motion
				pass
			else:
				aid		= RFIFOL(buf,2)
				dst		= RFIFOL(buf,6)
				tick	= RFIFOL(buf,10)
				sdelay	= RFIFOL(buf,14)
				ddelay	= RFIFOL(buf,18)
				damage	= RFIFOW(buf,22)
				p		= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@nomalattack_lower(dst: ({}), damage: {}, sDelay: {}, dDelay: {}, tick: {})\t// self\n".format(dst,damage,sdelay,ddelay,tick))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						if mobdata[p][aid][MOB.TICK] > 0:
							prev = tick
							tick = tick - mobdata[p][aid][MOB.TICK]
							mobdata[p][aid][MOB.TICK] = prev
						else:
							mobdata[p][aid][MOB.TICK] = tick
						self.text.AppendText("@nomalattack_lower(src: {}:\"{}\"({}), dst: ({}), damage: {}, sDelay: {}, dDelay: {}, tick: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME],aid,dst,damage,sdelay,ddelay,tick))
		elif num == 0x2e1 or num == 0x8c8:	#nomalattack
			type = RFIFOB(buf,29) if num == 0x8c8 else RFIFOB(buf,28)
			if type == 1 or type == 2 or type == 3:	#pickup/sitdown/standup motion
				pass
			else:
				aid		= RFIFOL(buf,2)
				dst		= RFIFOL(buf,6)
				tick	= RFIFOL(buf,10)
				sdelay	= RFIFOL(buf,14)
				ddelay	= RFIFOL(buf,18)
				damage	= RFIFOL(buf,22)
				p		= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@nomalattack(dst: ({}), damage: {}, sDelay: {}, dDelay: {}, tick: {})\t// self\n".format(dst,damage,sdelay,ddelay,tick))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						if mobdata[p][aid][MOB.TICK] > 0:
							prev = tick
							tick = tick - mobdata[p][aid][MOB.TICK]
							mobdata[p][aid][MOB.TICK] = prev
						else:
							mobdata[p][aid][MOB.TICK] = tick
						self.text.AppendText("@nomalattack(src: {}:\"{}\"({}), dst: ({}), damage: {}, sDelay: {}, dDelay: {}, tick: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME],aid,dst,damage,sdelay,ddelay,tick))
		elif num == 0x13e or num == 0x7fb:	#skill_casting
			aid		= RFIFOL(buf,2)
			dst		= RFIFOL(buf,6)
			skillid	= RFIFOW(buf,14)
			tick	= RFIFOL(buf,20)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillcasting(src: {}:\"{}\"({}), dst: {}, skill: \"{}\"({}), casttime: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME], aid, dst, getskill(skillid), skillid, tick))
		elif num == 0x1de:	#skill_damage
			skillid	= RFIFOW(buf,2)
			aid		= RFIFOL(buf,4)
			dst		= RFIFOL(buf,8)
			tick	= RFIFOL(buf,12)
			sdelay	= RFIFOL(buf,16)
			ddelay	= RFIFOL(buf,20)
			damage	= RFIFOL(buf,24)
			skilllv	= RFIFOW(buf,28)
			div_	= RFIFOW(buf,30)
			hit_	= RFIFOB(buf,32)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillattack(src: {}:\"{}\"({}), dst: ({}), skill: \"{}\"({}), skill_lv: {}, damage: {}, sDelay: {}, dDelay: {}, div: {}, hit: {}, tick: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME],aid,dst,getskill(skillid),skillid,skilllv,damage,sdelay,ddelay,div_,hit_,tick))
		elif num == 0x11a:	#skill_nodamage
			skillid	= RFIFOW(buf,2)
			val		= RFIFOW(buf,4)
			dst		= RFIFOL(buf,6)
			aid		= RFIFOL(buf,10)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillnodamage(src: {}:\"{}\"({}), dst: ({}), skill: \"{}\"({}), val: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME], aid, dst, getskill(skillid), skillid, val))
		elif num == 0x9cb:	#skill_nodamage
			skillid	= RFIFOW(buf,2)
			val		= RFIFOL(buf,4)
			dst		= RFIFOL(buf,8)
			aid		= RFIFOL(buf,12)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillnodamage(src: {}:\"{}\"({}), dst: ({}), skill: \"{}\"({}), val: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME], aid, dst, getskill(skillid), skillid, val))
		elif num == 0x117:	#skill_poseffect
			skillid	= RFIFOW(buf,2)
			aid		= RFIFOL(buf,4)
			val		= RFIFOW(buf,8)
			x		= RFIFOW(buf,10)
			y		= RFIFOW(buf,12)
			tick	= RFIFOL(buf,14)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillposeffect(src: {}:\"{}\"({}), skill: \"{}\"({}), val: {}, pos({}, {}), tick: {})\n".format(mobdata[p][aid][MOB.CLASS],mobdata[p][aid][MOB.NAME], aid, getskill(skillid), skillid, val, x, y, tick))
		elif num == 0x9ca:	#skill_unit
			aid		= RFIFOL(buf,8)
			x		= RFIFOW(buf,12)
			y		= RFIFOW(buf,14)
			unit_id	= RFIFOL(buf,16)
			skilllv	= RFIFOB(buf,22)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@skillunit_appeared(\""+mobdata[p][aid][MOB.NAME]+"\"(" +str(aid)+ "), pos("+str(x)+", "+str(y)+"), unit_id: "+str(hex(unit_id))+"), skill_lv: "+str(skilllv)+")\n")
		elif num == 0x080:	#clear_unit
			aid		= RFIFOL(buf,2)
			type	= RFIFOB(buf,6)
			p		= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					if type == 1:
						self.text.AppendText("@mob_defeated(\""+mobdata[p][aid][MOB.NAME]+"\"(" +str(aid)+ "))\n")
		elif num == 0xacc:	#gainexp
			exp		= RFIFOQ(buf,6)
			type	= RFIFOW(buf,14)
			quest	= RFIFOW(buf,16)
			if type==1:
				chrdata['BaseExp'] += exp
				self.text.AppendText("getexp "+str(exp)+",0," +str(quest)+ ";\n")
				self.statusbar.SetStatusText('BaseExp: {:>15,}'.format(chrdata['BaseExp']), 1)
			else:
				chrdata['JobExp'] += exp
				self.text.AppendText("getexp 0,"+str(exp)+"," +str(quest)+ ";\n")
				self.statusbar.SetStatusText('JobExp: {:>15,}'.format(chrdata['JobExp']), 2)
		elif num == 0x229:	#changeoption
			aid		= RFIFOL(buf,2)
			opt1	= RFIFOW(buf,6)
			opt2	= RFIFOW(buf,8)
			option	= RFIFOW(buf,10)
			karma	= RFIFOB(buf,14)
			p		= self.mapport.GetValue()
			s		= ""
			if p in npcdata.keys():
				if aid in npcdata[p].keys():
					if npcdata[p][aid][NPC.OPTION] == 2 or option == 2:
						s += "hideonnpc" if option == 2 else "hideoffnpc"
					elif npcdata[p][aid][NPC.OPTION] == 4 or option == 4:
						s += "cloakonnpc" if option == 4 else "cloakoffnpc"
					else:
						s += "hideoffnpc"
					s += " \""+npcdata[p][aid][NPC.NAME]+"\";\t// "+str(aid)
					npcdata[p][aid][NPC.OPTION] = option
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText(s+"\n")
			elif p in mobdata.keys():
				if aid in mobdata[p].keys():
					self.text.AppendText("@changeoption(id: "+str(aid)+", opt1: "+str(opt1)+", opt2: "+str(opt2)+", option: "+str(option)+", karma: "+str(karma)+")\n")
		elif num == 0x0c0:	#emotion
			aid		= RFIFOL(buf,2)
			type	= RFIFOB(buf,6)
			p		= self.mapport.GetValue()
			if chrdata['aid'] == aid:
				if self.scripttimer.IsChecked() == 1:
					self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
				self.text.AppendText("emotion "+str(type)+",\"\";\t// self\n")
			elif p in npcdata.keys():
				if aid in npcdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("emotion "+str(type)+",\""+npcdata[p][aid][NPC.NAME]+"\";\t// " +str(aid)+ "\n")
			elif self.prev_num == 0x1de or self.prev_num == 0x11a or self.prev_num == 0x117 or self.prev_num == 0x9cb or self.prev_num == 0x9ca or self.prev_num == 0x7fb:
				if p in mobdata.keys():
					if aid in mobdata[p].keys():
						if self.scripttimer.IsChecked() == 1:
							self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
						self.text.AppendText("@emotion "+str(type)+",\""+mobdata[p][aid][MOB.NAME]+"\";\t// " +str(aid)+ "\n")
		elif num == 0x19b or num == 0x1f3:	#misceffect
			aid		= RFIFOL(buf,2)
			type	= RFIFOL(buf,6)
			p		= self.mapport.GetValue()
			if chrdata['aid'] == aid:
				if self.scripttimer.IsChecked() == 1:
					self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
				self.text.AppendText("misceffect "+str(type)+",\"\";\t// self\n")
			elif p in npcdata.keys():
				if aid in npcdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("misceffect "+str(type)+",\""+npcdata[p][aid][NPC.NAME]+"\";\t// " +str(aid)+ "\n")
			elif p in mobdata.keys():
				if aid in mobdata[p].keys():
					if self.scripttimer.IsChecked() == 1:
						self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
					self.text.AppendText("@misceffect "+str(type)+",\""+mobdata[p][aid][MOB.NAME]+"\";\t// " +str(aid)+ "\n")
		elif num == 0x144:	#viewpoint
			aid		= RFIFOL(buf,2)
			type	= RFIFOL(buf,6)
			x		= RFIFOL(buf,10)
			y		= RFIFOL(buf,14)
			id		= RFIFOB(buf,18)
			color	= RFIFOL(buf,19)
			color	= color&0x00FFFFFF
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("viewpoint "+str(type)+", "+str(x)+", "+str(y)+", "+str(id)+", 0x"+format(color, '06X')+";\t// "+str(n)+"\n")
		elif num == 0x0d7:	#chatwnd
			p = self.mapport.GetValue()
			if p in npcdata.keys():
				aid		= RFIFOL(buf,4)
				if aid in npcdata[p].keys():
					s_len	= RFIFOW(buf,2)
					chatid	= RFIFOL(buf,8)
					if chatid in waitingroom.keys():
						pass
					else:
						s = buf[17*2:s_len*2]
						s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
						s = s.replace("\0","")
						waitingroom[chatid] = 1
						self.text.AppendText("waitingroom \""+s+"\", 0;\t// " +str(aid)+ "\n")
		elif num == 0x192:	#mapcell
			x		= RFIFOW(buf,2)
			y		= RFIFOW(buf,4)
			type	= RFIFOW(buf,6)
			s = buf[8*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			self.text.AppendText("setcell \"{}\", {}, {}, {};\n".format(s, x, y, type))
		elif num == 0x1d3:	#soundeffect
			s = buf[2*2:26*2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			type		= RFIFOB(buf,26)
			interval	= RFIFOL(buf,27)
			aid			= RFIFOL(buf,31)
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("soundeffect \""+s+"\", "+str(type)+", "+str(interval)+";\t// "+str(aid)+"\n")
		elif num == 0x7fe:	#musiceffect
			s = buf[2*2:26*2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("musiceffect \""+s+"\";\n")
		elif num == 0x0c4:	#npcshop
			aid	= RFIFOL(buf,2)
			self.tmp_id = aid
		elif num == 0x0c6:	#npcshop2
			i = 0
			s = ""
			while i*13+4 < p_len:
				if i > 0:
					s += ","
				s	+= str(RFIFOL(buf,13+i*13))
				s	+= ":"
				s	+= str(RFIFOL(buf,4+i*13))
				i += 1
			aid = self.tmp_id
			p = self.mapport.GetValue()
			if aid == 0:
				m = chrdata["mapname"]
				self.text.AppendText("-\tshop\t"+ m[:-4] +"#callshop\t-1," +s +"\t// selfpos("+ str(chrdata["x"])+", "+ str(chrdata["y"]) +")\n")
			else:
				if p in npcdata.keys():
					if aid in npcdata[p].keys():
						self.text.AppendText(npcdata[p][aid][NPC.MAP]+","+ str(npcdata[p][aid][NPC.POSX]) + ","+ str(npcdata[p][aid][NPC.POSY]) +","+ str(npcdata[p][aid][NPC.POSD]) +"\tshop\t"+ str(npcdata[p][aid][NPC.NAME]) +"\t"+ str(npcdata[p][aid][NPC.CLASS]) + "," +s +"\t// "+ str(aid) +"\n")
			self.tmp_id = 0
		elif num == 0x0b1:	#updatestatus
			type	= RFIFOW(buf,2)
			value	= RFIFOL(buf,4)
			if type == 20:	#Zeny
				zeny = value - chrdata['Zeny']
				if chrdata['Zeny'] >= 0:
					self.text.AppendText('set Zeny, Zeny {:>+};\n'.format(zeny))
				else:
					self.text.AppendText('@update_status(Zeny: {} ({:=+}))\n'.format(value, zeny))
				chrdata['Zeny'] = value
				self.statusbar.SetStatusText('Zeny: {:>15,}'.format(chrdata['Zeny']), 3)
		elif num == 0xacb:	#updatestatus
			type	= RFIFOW(buf,2)
			value	= RFIFOQ(buf,4)
			if type == 1:	#BaseExp
#				if chrdata['BaseExp'] >= 0:
#					exp = value - chrdata['BaseExp']
#					self.text.AppendText("getexp "+str(exp)+",0;\t// "+str(value)+"\n")
#				else:
#					self.text.AppendText("@update_status(BaseExp: "+str(value)+")\n")
				chrdata['BaseExp'] = value
				self.statusbar.SetStatusText('BaseExp: {:>15,}'.format(chrdata['BaseExp']), 1)
			elif type == 2:	#JobExp
#				if chrdata['JobExp'] >= 0:
#					exp = value - chrdata['JobExp']
#					self.text.AppendText("getexp "+str(exp)+",0;\t// "+str(value)+"\n")
#				else:
#					self.text.AppendText("@update_status(JobExp: "+str(value)+")\n")
				chrdata['JobExp'] = value
				self.statusbar.SetStatusText('JobExp: {:>15,}'.format(chrdata['JobExp']), 2)
		elif num == 0x82d:	#charactor_select
			pass
		elif num == 0x9a0:	#charactor_select
			pass
		elif num == 0x99d:	#charactor_select
			c_len	= RFIFOW(buf,2)
			if c_len == 4:
				pass
			else:
				i = 4
				j = 0
				while i < c_len:
					char_num = RFIFOW(buf,122+j*155)
					s = buf[(92+j*155)*2:(92+24+j*155)*2]
					s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
					s = s.replace("\0","")
					chrselect[char_num] = {'Char_id': RFIFOL(buf,4+j*155), 'Char_Name': s, 'BaseExp': RFIFOQ(buf,8+j*155), 'Zeny': RFIFOL(buf,16+j*155), 'JobExp': RFIFOQ(buf,20+j*155) }
					self.text.AppendText("[No,{}, ID:{}, Name:\"{}\"]\n".format(char_num, chrselect[char_num]['Char_id'], s))
					i += 155
					j += 1
		elif num == 0x71:	#charactor_select
			aid	= RFIFOL(buf,2)
			s = buf[2*6:p_len*2-16]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			port	= RFIFOW(buf,26)
			chrdata['mapname'] = s
			self.mapport.SetValue(str(port))
			self.th.setport(int(self.charport.GetValue()), int(self.mapport.GetValue()))
			self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
			i = 0
			while i < 15:
				if not i in chrselect.keys():
					chrselect[i] = dummy_chr
				elif chrselect[i]['Char_id'] == aid:
					chrdata['BaseExp'] = chrselect[i]['BaseExp']
					self.statusbar.SetStatusText('BaseExp: {:>15,}'.format(chrdata['BaseExp']), 1)
					chrdata['JobExp'] = chrselect[i]['JobExp']
					self.statusbar.SetStatusText('JobExp: {:>15,}'.format(chrdata['JobExp']), 2)
					chrdata['Zeny'] = chrselect[i]['Zeny']
					chrdata['name'] = chrselect[i]['Char_Name']
					self.statusbar.SetStatusText('Zeny: {:>15,}'.format(chrdata['Zeny']), 3)
					self.text.AppendText("No.{} selected.\n".format(i))
				i += 1
		elif num == 0x91:	#changemap
			s = buf[2*2:p_len*2-8]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			x	= RFIFOW(buf,18)
			y	= RFIFOW(buf,20)
			#if s[-4:] == ".gat":
			i = s.find('.gat')
			if i >= 0:
				s = s[:i+4]
				aid = self.CheckNearNPC(chrdata['mapname'], chrdata['x'], chrdata['y']);
				p = self.mapport.GetValue()
				if aid >= 0:
					if p in warpnpc.keys():
						if aid in warpnpc[p].keys():
							self.text.AppendText("@changemap \"{}\", x : {}, y : {};\t// from: {}({}, {})\n".format(s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
						else:
							self.text.AppendText("{},{},{},0\twarp\t{}\t2,2,{},{},{} //{} from_pos=({}, {})\n".format(
								npcdata[p][aid][NPC.MAP],npcdata[p][aid][NPC.POSX],npcdata[p][aid][NPC.POSY],npcdata[p][aid][NPC.NAME], s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
							warpnpc[p][aid] = npcdata[p][aid][NPC.NAME]
					else:
						self.text.AppendText("{},{},{},0\twarp\t{}\t2,2,{},{},{} //{} from_pos=({}, {})\n".format(
							npcdata[p][aid][NPC.MAP],npcdata[p][aid][NPC.POSX],npcdata[p][aid][NPC.POSY],npcdata[p][aid][NPC.NAME], s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
						warpnpc[p] = { aid: npcdata[p][aid][NPC.NAME] }
				else:
					self.text.AppendText("warp \"{}\", {}, {};\t// from: {}({}, {})\n".format(s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
				chrdata['mapname'] = s
				chrdata['x'] = x
				chrdata['y'] = y
				self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
			else:
				self.text.AppendText("@changemap Failed packet\n")
		elif num == 0x92:	#changemapserver
			s = buf[2*2:p_len*2-20]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			x	= RFIFOW(buf,18)
			y	= RFIFOW(buf,20)
			port	= RFIFOW(buf,26)
			#if s[-4:] == ".gat":
			i = s.find('.gat')
			if i >= 0:
				s = s[:i+4]
				aid = self.CheckNearNPC(chrdata['mapname'], chrdata['x'], chrdata['y']);
				p = self.mapport.GetValue()
				if aid >= 0:
					if p in warpnpc.keys():
						if aid in warpnpc[p].keys():
							self.text.AppendText("@changemapserver \"{}\", x : {}, y : {}, port : {};\t// from: {}({}, {})\n".format(s, x, y, port, chrdata['mapname'], chrdata['x'], chrdata['y']))
						else:
							self.text.AppendText("{},{},{},0\twarp\t{}\t2,2,{},{},{} //{} from_pos=({}, {})\n".format(
								npcdata[p][aid][NPC.MAP],npcdata[p][aid][NPC.POSX],npcdata[p][aid][NPC.POSY],npcdata[p][aid][NPC.NAME], s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
							warpnpc[p][aid] = [npcdata[p][aid][NPC.NAME]]
					else:
						self.text.AppendText("{},{},{},0\twarp\t{}\t2,2,{},{},{} //{} from_pos=({}, {})\n".format(
							npcdata[p][aid][NPC.MAP],npcdata[p][aid][NPC.POSX],npcdata[p][aid][NPC.POSY],npcdata[p][aid][NPC.NAME], s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y']))
						warpnpc[p] = { aid: [npcdata[p][aid][NPC.NAME]] }
				else:
					self.text.AppendText("warp \"{}\", {}, {};\t// from: {}({}, {}) port : {}\n".format(s, x, y, chrdata['mapname'], chrdata['x'], chrdata['y'], port))
				chrdata['mapname'] = s
				chrdata['x'] = x
				chrdata['y'] = y
				self.mapport.SetValue(str(port))
				self.th.setport(int(self.charport.GetValue()), int(self.mapport.GetValue()))
				self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
			else:
				self.text.AppendText("@changemapserver Failed packet. \"{}\", x : {}, y : {}, port : {};\n".format(s, x, y, port))
		elif num == 0x087:	#walk
			x = int(((int(buf[8*2:8*2+2],16)&0xF)<<6) + (int(buf[9*2:9*2+2],16)>>2))
			y = int(((int(buf[9*2:9*2+2],16)&0x3)<<8) + int(buf[10*2:10*2+2],16))
			chrdata['x'] = x
			chrdata['y'] = y
			self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
		elif num == 0x088:	#fixpos
			aid	= RFIFOL(buf,2)
			x	= RFIFOW(buf,6)
			y	= RFIFOW(buf,8)
			if chrdata['aid'] == aid:
				chrdata['x'] = x
				chrdata['y'] = y
				self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
		elif num == 0x2eb or num == 0xa18:	#authok
			x	= RFIFOPOSX(buf,6)
			y	= RFIFOPOSY(buf,6)
			chrdata['x'] = x
			chrdata['y'] = y
			self.statusbar.SetStatusText(chrdata['mapname']+':('+str(chrdata['x'])+', '+str(chrdata['y'])+")", 0)
		elif num == 0x08d:	#message
			s = buf[8*2:p_len*2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			if chrdata['name'] != 'unknown name':
				s = s.replace(chrdata['name'],"\"+strcharinfo(0)+\"")
			aid	= RFIFOL(buf,4)
			p	= self.mapport.GetValue()
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if chrdata['aid'] == aid:
				self.text.AppendText("unittalk getcharid(3),\""+s+"\",1;\t// self:hidden\n")
			elif p in npcdata.keys() and aid in npcdata[p].keys():
				self.text.AppendText("unittalk getnpcid(0,\""+npcdata[p][aid][NPC.NAME]+"\"),\""+s+"\";\t// " +str(aid)+ "\n")
			elif p in mobdata.keys() and aid in mobdata[p].keys():
				self.text.AppendText("unittalk '@mob_id,\""+s+"\";\t// " +str(aid)+ ":" +mobdata[p][aid][MOB.NAME]+ "\n")
			else:
				self.text.AppendText("@unittalk \""+s+"\";\t// " +str(aid)+ "\n")
		elif num == 0x08e:	#message
			s = buf[4*2:p_len*2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			if chrdata['name'] != 'unknown name':
				s = s.replace(chrdata['name'],"\"+strcharinfo(0)+\"")
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("unittalk getcharid(3),\""+s+"\",1;\t// self:hidden\n")
		elif num == 0x2c1:	#multicolormessage
			s = buf[12*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			aid	= RFIFOL(buf,4)
			color	= RFIFOL(buf,8)
			color = (int(color,16) & 0x0000FF) >> 16 | (int(color,16) & 0x00FF00) | (int(color,16) & 0xFF0000) << 16;
			p	= self.mapport.GetValue()
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					self.text.AppendText("@monstertalk \""+s+"\", color: " +str(color)+ ", id: " +str(aid)+ "\n")
			else:
				self.text.AppendText("@talk \""+s+"\", color: " +str(color)+ ", id: " +str(aid)+ "\n")
		elif num == 0x8b3:	#showscript
			s = buf[8*2:p_len*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			aid	= RFIFOL(buf,4)
			p	= self.mapport.GetValue()
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			if chrdata['aid'] == aid:
				self.text.AppendText("showmessage \""+s+",\",\"\";\t// self:hidden\n")
			elif p in npcdata.keys():
				if aid in npcdata[p].keys():
					self.text.AppendText("showmessage \""+s+"\",\""+npcdata[p][aid][NPC.NAME]+"\";\t// " +str(aid)+ "\n")
			elif p in mobdata.keys():
				if aid in mobdata[p].keys():
					self.text.AppendText("@showmessage \""+s+"\";\t// " +str(aid)+ ":" +mobdata[p][aid][MOB.NAME]+ "\n")
		elif num == 0xa37:	#getitem
			upgrade = 0
			idx		= RFIFOW(buf,2)
			amount	= RFIFOW(buf,4)
			itemid	= RFIFOL(buf,6)
			limit	= RFIFOL(buf,35)

			equip	= RFIFOL(buf,29)
			if equip > 0:
				identify	= RFIFOB(buf,10)
				refine	= RFIFOB(buf,12)
				card1	= RFIFOL(buf,13)
				card2	= RFIFOL(buf,17)
				card3	= RFIFOL(buf,21)
				card4	= RFIFOL(buf,25)
				opt1id	= RFIFOW(buf,41)
				opt1val	= RFIFOW(buf,43)
				opt2id	= RFIFOW(buf,46)
				opt2val	= RFIFOW(buf,48)
				opt3id	= RFIFOW(buf,51)
				opt3val	= RFIFOW(buf,53)
				opt4id	= RFIFOW(buf,56)
				opt4val	= RFIFOW(buf,58)
				opt5id	= RFIFOW(buf,61)
				opt5val	= RFIFOW(buf,63)
				if refine > 0 or card1 > 0 or card2 > 0 or card3 > 0 or card4 > 0:
					upgrade = 1
				if opt1id > 0:
					upgrade = 2
			if idx in inventory['item'].keys():
				nameid = inventory['item'][idx]["Nameid"]
				if itemid == nameid:
					n = inventory['item'][idx]["Amount"]
					inventory['item'][idx]["Amount"] = n + amount
					if upgrade == 2:
						self.text.AppendText("getoptitem {},{},{},0,{},{},{},{},0,{};\t//opt: {},{}, {},{}, {},{}, {},{}, {},{};\n".format(itemid,identify,refine,card1,card2,card3,card4,limit,getrandopt(opt1id),opt1val,getrandopt(opt2id),opt2val,getrandopt(opt3id),opt3val,getrandopt(opt4id),opt4val,getrandopt(opt5id),opt5val))
					elif upgrade == 1:
						self.text.AppendText("getitem2 {},{},{},{},0,{},{},{},{},{};\n".format(itemid,amount,identify,refine,card1,card2,card3,card4,limit))
					else:
						self.text.AppendText("getitem {},{};\n".format(itemid,amount))
				else:
					if upgrade == 2:
						self.text.AppendText("@getoptitem {},{},{},0,{},{},{},{},0,{};\t//unexpected error opt: {},{}, {},{}, {},{}, {},{}, {},{};\n".format(itemid,identify,refine,card1,card2,card3,card4,limit,getrandopt(opt1id),opt1val,getrandopt(opt2id),opt2val,getrandopt(opt3id),opt3val,getrandopt(opt4id),opt4val,getrandopt(opt5id),opt5val))
					elif upgrade == 1:
						self.text.AppendText("@getitem2 {},{},{},{},0,{},{},{},{},{};\t//unexpected error\n".format(itemid,amount,identify,refine,card1,card2,card3,card4,limit))
					else:
						self.text.AppendText("@getitem {},{};\t//unexpected error\n".format(itemid,amount))
			else:
				inventory['item'][idx] = {"Nameid": itemid, "Amount": amount}
				if upgrade == 2:
					self.text.AppendText("getoptitem {},{},{},0,{},{},{},{},0,{};\t//opt: {},{}, {},{}, {},{}, {},{}, {},{};\n".format(itemid,identify,refine,card1,card2,card3,card4,limit,getrandopt(opt1id),opt1val,getrandopt(opt2id),opt2val,getrandopt(opt3id),opt3val,getrandopt(opt4id),opt4val,getrandopt(opt5id),opt5val))
				elif upgrade == 1:
					self.text.AppendText("getitem2 {},{},{},{},0,{},{},{},{},{};\n".format(itemid,amount,identify,refine,card1,card2,card3,card4,limit))
				else:
					self.text.AppendText("getitem {},{};\n".format(itemid,amount))
		elif num == 0x0af or num == 0x229:	#delitem

			idx		= RFIFOW(buf,2)
			amount	= RFIFOW(buf,4)
			if idx in inventory['item'].keys():
				nameid = inventory['item'][idx]["Nameid"]
				values = inventory['item'][idx]["Amount"] - amount
				if values <= 0:
					del inventory['item'][idx]
				else:
					inventory['item'][idx]["Amount"] = values
				self.text.AppendText("delitem {},{};\n".format(nameid,amount))
			else:
				self.text.AppendText("@delitem idx:{},{};\t//NotFound\n".format(idx,amount))
		elif num == 0x7fa:	#delitem
			idx		= RFIFOW(buf,4)
			amount	= RFIFOW(buf,6)
			if idx in inventory['item'].keys():
				nameid = inventory['item'][idx]["Nameid"]
				values = inventory['item'][idx]["Amount"] - amount
				if values <= 0:
					del inventory['item'][idx]
				else:
					inventory['item'][idx]["Amount"] = values
				self.text.AppendText("delitem {},{};\n".format(nameid,amount))
			else:
				self.text.AppendText("@delitem idx:{},{};\t//NotFound\n".format(idx,amount))
		elif num == 0x2cb:	#mdcreate
			s = buf[2*2:63*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			self.text.AppendText("mdcreate \"{}\";\n".format(s))
		elif num == 0x983:	#status_change
			type	= RFIFOW(buf,2)
			aid		= RFIFOL(buf,4)
			flag	= RFIFOB(buf,8)
			mtick	= RFIFOL(buf,9)
			tick	= RFIFOL(buf,13)
			val1	= RFIFOL(buf,17)
			val2	= RFIFOL(buf,21)
			val3	= RFIFOL(buf,25)
			if mtick == 9999:
				pass
			else:
				p	= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@sc_start3 {},{},{},{},0,{},{};\t// self, tick={}\n".format(getefst(type),val1,val2,val3,mtick,flag,tick))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						self.text.AppendText("@sc_start3 {},{},{},{},0,{},{};\t// {}, tick={}\n".format(getefst(type),val1,val2,val3,mtick,flag,aid,tick))
		elif num == 0x43f:	#status_change
			type	= RFIFOW(buf,2)
			aid		= RFIFOL(buf,4)
			flag	= RFIFOB(buf,8)
			tick	= RFIFOL(buf,9)
			val1	= RFIFOL(buf,13)
			val2	= RFIFOL(buf,17)
			val3	= RFIFOL(buf,21)
			if tick == 9999:
				pass
			else:
				p	= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@sc_start3 {},{},{},{},0,{},{};\t// self\n".format(getefst(type),val1,val2,val3,tick,flag))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						self.text.AppendText("@sc_start3 {},{},{},{},0,{},{};\t// {}\n".format(getefst(type),val1,val2,val3,tick,flag,aid))
		elif num == 0x8ff:	#seteffect_enter
			aid		= RFIFOL(buf,2)
			type	= RFIFOW(buf,6)
			tick	= RFIFOL(buf,8)
			val1	= RFIFOL(buf,12)
			val2	= RFIFOL(buf,16)
			val3	= RFIFOL(buf,20)
			if tick == 9999 or type == 993:
				pass
			else:
				p	= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@effect_enter {},{},{},{},0,{};\t// self\n".format(getefst(type),val1,val2,val3,tick))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						self.text.AppendText("@effect_enter {},{},{},{},0,{},{};\t// {}\n".format(getefst(type),val1,val2,val3,tick,flag,aid))
		elif num == 0x984:	#seteffect_enter
			aid		= RFIFOL(buf,2)
			type	= RFIFOW(buf,6)
			mtick	= RFIFOL(buf,8)
			tick	= RFIFOL(buf,12)
			val1	= RFIFOL(buf,16)
			val2	= RFIFOL(buf,20)
			val3	= RFIFOL(buf,24)
			if mtick == 9999 or type == 993:
				pass
			else:
				p	= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					self.text.AppendText("@effect_enter {},{},{},{},0,{};\t// self\n".format(getefst(type),val1,val2,val3,mtick))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						self.text.AppendText("@effect_enter {},{},{},{},0,{};\t// {}\n".format(getefst(type),val1,val2,val3,mtick,aid))
		elif num == 0x196:	#status_load
			type	= RFIFOW(buf,2)
			aid		= RFIFOL(buf,4)
			flag	= RFIFOB(buf,8)
			if type == 46 or type == 622 or type == 673 or type == 993:
				pass
			else:
				p	= self.mapport.GetValue()
				if chrdata['aid'] == aid:
					if flag == 0:
						self.text.AppendText("@sc_end {};\t// self\n".format(getefst(type)))
					else:
						self.text.AppendText("@status_load type: {}, flag: {}\t// self\n".format(getefst(type),flag))
				elif p in mobdata.keys():
					if aid in mobdata[p].keys():
						if flag == 0:
							self.text.AppendText("sc_end {},{};\n".format(getefst(type),aid))
						else:
							self.text.AppendText("@status_load type: {}, aid: {}, flag: {}\t\n".format(getefst(type),aid,flag))
		elif num == 0xadf:	#charname_req
			aid			= RFIFOL(buf,2)
			group_id	= RFIFOL(buf,6)
			s = buf[10*2:34*2-2]
			s = binascii.unhexlify(s.encode('utf-8')).decode('cp932','ignore')
			s = s.replace("\0","")
			if group_id != 0:
				self.text.AppendText("//setgroupid "+ str(group_id) + ";\t// " +str(aid)+ "\n")
			t = buf[34*2:58*2-2]
			t = binascii.unhexlify(t.encode('utf-8')).decode('cp932','ignore')
#			t = t.replace("\0","")
			if t[0] != "\0":
				self.text.AppendText("//settitle "+ t + ";\n// " +str(aid)+ "\n")
		elif num == 0xa24:	#acievement update
			nameid = RFIFOL(buf,16)
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("achievement {};\n".format(nameid))
		elif num == 0xab9:	#itempreview
			index = RFIFOW(buf,2) - 2
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("itempreview {};\n".format(index))
		elif num == 0xb13:	#itempreview
			index = RFIFOW(buf,2) - 2
			if self.scripttimer.IsChecked() == 1:
				self.text.AppendText('/* ' + str(datetime.now().time()) + ' */\t')
			self.text.AppendText("itempreview {};\n".format(index))
		elif num == 0x1d6:	#mapproperty
			type = RFIFOW(buf,2)
			self.text.AppendText("@mapproperty map: "+chrdata['mapname']+", type: "+ str(type) + "\n")
		elif num == 0x99b:	#mapproperty_r
			type	= RFIFOW(buf,2)
			bit		= RFIFOL(buf,4)
			self.text.AppendText("@mapproperty_r map: "+chrdata['mapname']+", type: "+ str(type) + ", bit: "+ str(hex(bit)) +"\n")
		elif num == 0x977:	#hp_info
			aid		= RFIFOL(buf,2)
			hp		= RFIFOL(buf,6)
			maxhp	= RFIFOL(buf,10)
			p	= self.mapport.GetValue()
			if p in mobdata.keys():
				if aid in mobdata[p].keys():
					self.text.AppendText("@hpinfo name: "+ mobdata[p][aid][MOB.NAME] + ", class: "+ str(mobdata[p][aid][MOB.CLASS]) +", HP: " +str(hp)+ "/" +maxhp+ "\n")
		elif num == 0xa36:	#hp_info_tiny
			aid	= RFIFOL(buf,2)
			per	= RFIFOB(buf,6)
			per	= int(per) * 5
			p	= self.mapport.GetValue()
			self.text.AppendText("@hp_info_tiny name: "+ mobdata[p][aid][MOB.NAME] + ", class: "+ str(mobdata[p][aid][MOB.CLASS]) +", per: "+ str(per) +"%\n")
		elif num == 0x283:	#account_id
			aid	= RFIFOL(buf,2)
			chrdata['aid'] = aid
		elif num == 0xb09 or num == 0xb0a:	#inventory
			s_len = RFIFOW(buf,2)
			type = RFIFOB(buf,4)
			if type == 0:
				c = 34 if num == 0xb09 else 67
				i = 0
				while i*c+5 < s_len:
					idx    = RFIFOW(buf, i*c+5)
					nameid = RFIFOL(buf, i*c+7)
					amount = RFIFOW(buf, i*c+12) if num == 0xb09 else 1
					inventory['item'][idx] = {"Nameid": nameid, "Amount": amount}
					i += 1
		elif num == 0x446:	#showevent
			aid	= RFIFOL(buf,2)
			x	= RFIFOW(buf,6)
			y	= RFIFOW(buf,8)
			state	= RFIFOW(buf,10)
			type	= RFIFOW(buf,12)
			p	= self.mapport.GetValue()
			if p in npcdata.keys():
				if aid in npcdata[p].keys():
					self.text.AppendText("showevent "+str(state)+", "+str(type)+", "+npcdata[p][aid][NPC.NAME]+";\t// " +str(aid)+ ": "+str(x)+", "+str(y)+"\n")
				else:
					self.text.AppendText("@showevent "+str(state)+", "+str(type)+";\t// " +str(aid)+ ": "+str(x)+", "+str(y)+"\n")
			else:
				self.text.AppendText("@showevent "+str(state)+", "+str(type)+"\";\t// " +str(aid)+ ": "+str(x)+", "+str(y)+"\n")
		elif Configuration['Show_OtherPacket'] == 1:
			self.text.AppendText("@packet "+ n + ".\n")

app = wx.App()
read_packet_db()
read_ignore_db()
read_config_db()
read_ip_db()
MARiA_Frame(None, -1, "MARiA  "+MARiA_VERSION)
app.MainLoop()
