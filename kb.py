_B=None
_A=True
import os,sys,termios,abc,subprocess
from enum import Enum
import yaml,zlib
class Color:FG_Black=30;FG_Red=31;FG_Green=32;FG_Yellow=33;FG_Blue=34;FG_Magenta=35;FG_Cyan=36;FG_White=37;Reset=0;BG_Black=40;BG_Red=41;BG_Green=42;BG_Yellow=43;BG_Blue=44;BG_Magenta=45;BG_Cyan=46;BG_White=47
class Key:
	def readchar():ch=sys.stdin.read(1);return ch
	def readkey():
		c1=Key.readchar()
		if c1 in'\x03':raise KeyboardInterrupt
		if c1!='\x1b':return c1
		c2=Key.readchar()
		if c2 not in'O[':return c1+c2
		c3=Key.readchar()
		if c3 not in'12356':return c1+c2+c3
		c4=Key.readchar()
		if c4 not in'01345789':return c1+c2+c3+c4
		c5=Key.readchar();return c1+c2+c3+c4+c5
	def send(buf,flush=False):
		sys.stdout.write(buf)
		if flush:sys.stdout.flush()
	def send_color(buf,color):tmp='%s%dm%s%s%dm'%(Key.ESCAPE_STR,color,buf,Key.ESCAPE_STR,Color.Reset);Key.send(tmp)
	def send_color256(buf,color):tmp='%s48;5;%dm%s%s%dm'%(Key.ESCAPE_STR,color,buf,Key.ESCAPE_STR,Color.Reset);Key.send(tmp)
	def setpos(row=1,col=1):
		if row<=1 and col<=1:tmp=Key.ESCAPE_STR+'H'
		tmp='%s%d;%dH'%(Key.ESCAPE_STR,row,col);Key.send(tmp,_A)
	ESCAPE_STR='\x1b[';CLEAN=ESCAPE_STR+'2J';UP=ESCAPE_STR+'A';DOWN=ESCAPE_STR+'B';RIGHT=ESCAPE_STR+'C';LEFT=ESCAPE_STR+'D';CLEAN_SET=CLEAN+ESCAPE_STR+'H';ARROW=[UP,DOWN,RIGHT,LEFT]
class SelectType(Enum):Empty=' ',Color.Reset;Some='+',Color.BG_Cyan;Full='*',Color.BG_Blue
class Card:
	def __init__(self,name='',value=_B):self.parent=_B;self._select=SelectType.Empty;self.name=name;self.children=[];self.script=value.get('script','');self.prologue=value.get('prologue','')
	def generate(self):return self.prologue,self.script
	@property
	def select(self):return self._select
	@select.setter
	def select(self,new_type):self._select=new_type
class Cassette(Card):
	def parse(name,value):
		A='children'
		if value!=_B and A in value:
			curr=Cassette(name=name,value=value)
			for (sub_name,sub_val) in value[A].items():child=Cassette.parse(sub_name,sub_val);child.parent=curr;curr.children.append(child)
		else:
			if value==_B:value={}
			curr=Card(name=name,value=value)
		return curr
	def __init__(self,name,value):super().__init__(name,value)
	def generate(self):
		run_prologue=self.prologue;run_script=''
		for child in self.children:
			if child.select!=SelectType.Empty:child_prologue,child_script=child.generate();run_prologue+=child_prologue;run_script+=child_script
		run_script+=self.script;return run_prologue,run_script
	@property
	def select(self):
		cnt=sum([1 for item in self.children if item.select!=SelectType.Empty])
		if cnt==len(self.children):self._select=SelectType.Full
		elif cnt==0:self._select=SelectType.Empty
		else:self._select=SelectType.Some
		return self._select
	@select.setter
	def select(self,new_type):
		self._select=new_type
		for card in self.children:card.select=new_type
class RawDialog(abc.ABC):
	def init_termios(self):fd_in=sys.stdin.fileno();self.old_settings=termios.tcgetattr(fd_in);term=termios.tcgetattr(fd_in);term[3]&=~(termios.ICRNL|termios.IXON);term[3]&=~ termios.OPOST;term[3]&=~(termios.ICANON|termios.ECHO|termios.IGNBRK|termios.BRKINT);termios.tcsetattr(fd_in,termios.TCSAFLUSH,term)
	def __init__(self):self.init_termios();self.x,self.y=1,1;term_size=os.get_terminal_size();self.size=term_size.columns,term_size.lines
	def flushpos(self):Key.setpos(self.y,self.x)
	def run(self):
		while _A:
			self.display()
			try:key=Key.readkey();self.key_event(key)
			except KeyboardInterrupt:termios.tcsetattr(sys.stdin,termios.TCSADRAIN,self.old_settings);break
	@abc.abstractmethod
	def display(self):0
	@abc.abstractmethod
	def key_event(self,key):0
class Kickback(RawDialog):
	banner=' _      _         _        _                    _\n| |    (_)       | |      | |                  | |\n| |  _  _   ____ | |  _   | |__   _____   ____ | |  _\n| |_/ )| | / ___)| |_/ )  |  _ \\ (____ | / ___)| |_/ )\n|  _ ( | |( (___ |  _ (   | |_) )/ ___ |( (___ |  _ (\n|_| \\_)|_| \\____)|_| \\_)  |____/ \\_____| \\____)|_| \\_)\n\n';offset_y=banner.count('\n');bottom_msg='Tip: <Space> select. (S)tart script. (C)heck current script. (q)uit~'
	def __init__(self,data):super().__init__();self.root=Cassette.parse('',data);self.curr=self.root;self.update_area()
	def update_area(self):self.x,self.y=2,1;self.max_y=len(self.curr.children)
	def key_event(self,key):
		if key=='q':raise KeyboardInterrupt
		elif key==' ':
			if self.curr_card.select==SelectType.Empty:self.curr_card.select=SelectType.Full
			else:self.curr_card.select=SelectType.Empty
		elif key=='S':self.run_cmd()
		elif key=='C':Key.send(Key.CLEAN_SET,_A);combine_sh=''.join(self.root.generate());print(combine_sh);Key.readkey()
		elif key==Key.UP:self.y=max(1,self.y-1)
		elif key==Key.DOWN:self.y=min(self.y+1,self.max_y)
		elif key==Key.LEFT:
			if self.curr.parent!=_B:self.curr=self.curr.parent;self.update_area()
		elif key==Key.RIGHT:
			if len(self.curr_card.children)!=0:self.curr=self.curr_card;self.update_area()
	@property
	def curr_card(self):return self.curr.children[self.y-1]
	def run_cmd(self):combine_sh=''.join(self.root.generate());Key.send(Key.CLEAN_SET,_A);proc=subprocess.Popen(['/bin/bash','-c',combine_sh]);proc.wait();raise KeyboardInterrupt
	def show_card(self,card):
		Key.send('[%s] '%card.select.value[0]);Key.send_color('%s'%card.name,card.select.value[1])
		if len(card.children)!=0:Key.send(' >')
		Key.send('\r\n',_A)
	def display(self):
		Key.send(Key.CLEAN_SET+Kickback.banner)
		for card in self.curr.children:self.show_card(card)
		Key.setpos(999,1);Key.send(self.bottom_msg);self.flushpos()
	def flushpos(self):Key.setpos(self.y+Kickback.offset_y,self.x)
if __name__=='__main__':
	compress_data=b'x\xda\xb5V]\x8b\xdb:\x10}\xdf_1\x84\x94\xecRdq\xb9e)\x0bY\n-\x85\x0b\x85\x0b\xbb\xf7>\xb5%\xc8\x92l\xabQ,W\x92\xf3\xd1v\xfb\xdb;\xb2cG\xeb$\xddd\xa1y\x89=\x9as\xe6Cg&\xe1\x85\xd2\xc2\xca\xf2\xe6\x02\x80U>|\x01T\xd6h\x93\xd7\xf2\x06~4\xef\xcd\xd1\xac\x9a\xe73\xad\x9c\x9f^^5V\xc7\xadBD\xef\xe3ja\x82#\xa8\xd2y\xa65\x90\r\x8c\xbf\xc7\xc8\x8fo>?4\xce<\x8a\x1a>\xdf\\\xd1=\xee\xf3\x0e\xe3\xbf\x9c^\x8e\x100\xba\xda\x9es\xcd\xca\xfc<x\x03\xe9\t\x16l.\xcf\xc3\x07D\x0f\xaf6\xbe0\xe5\xdf\xa4R\xd5y,\x11\xb0\'+\xa5_\x19;\'\xde\x18\xbdc\x1b\xf6\xab\xb1\xd5V\xc7\xef\x87c\x1e\xac\x1e\x91}\xc0\xf0Y\xe5\xd2?\x8f* \x1fQa\xfeM\xee\xeey|=\xbc\'\x15\x86\xcf\xa5=\xaf\xb1-&Q\xa6g\xc9Ez\x1e\x05\x02z\xb0_\xd4\xeb\xf3\xd0\x01\x11]\xa9Y\xaa\xc5y\x04-&\xea\xec\xfeH\xeeFN\x08\x82xbee\x9c\xf2\xc6n\xa0\xaa\xd8MKA\xf0\x91\xe28\xa6Z\xe2<\xeeAqZ\xebJ0/\xbb\\\x8d\x90_\xa2\xbb;\x1c\xf6\xdd?\xf7\xff\xdd\xfd;\x1d_j\x97\xce\xac\xd4\x929d\xe7@\\,\x85\xb9\xdcXU\xe6\xd3\t\xad\x9d\xa5\xae`V\xd2\xad\xcdMb\xc9`\xcc\x19\x1e\xccP\x96\xd3Q\xe1}\xe5n(\x152M\xc2\x893\xb5\xe52\xe1fA\xf3*G7\x1aY\xd1\x92\xa0i\x14\xb1i\xc3\x99\x9eu\x9c\xd3\xd1x\x1br\x00\x1b\r[\x912W\x84\x1a\x9a\xe9\xc0J`\x1c\xe7\x05?\x00A@\x88\x90\xcc.\x8c\xc5w/%\x8c\x1fG\x83[L{I\xcbZ\xeb\xe3\xfc\x92\x17\x06&X\x1e|t*/\xa5 \xe9f: \xfa\x0c\xbfiC\xe3\xf4\xd7u\xb2\xc6\xed\xda\xde\xc4\x03\xae0UN\xe0\x16\xa8\xf4\x9c\xe2\xad\xd2\xd6\xdf%AP\x89\x88\x8b\x0f\x96\x13\xb2#\xce\xf2?\x90\xe1\xf3S\xdc\xd3*NQ\x8e\x9a?o\xb0\xb6\xa0f\xb2l\xed\xb6ko\x88l4\xd0\x15\xe8\x8a$x\xd6Ub\x1d\n\xe3>\xc3\xcbw\xc5E\xb7\x9a\x08V\x8c\x83\'\x0f3\x85\x05\xd93\xe5\xca\x17u\xda\xb4\xa8\xc5\xd2-\x96n\x87\xc8Q\x8d\xf59\x8f\xc7\xabR\x1b&\xe8\xe3\x18D\xab\xb2^\x93\xf5\xeb\xeb\xd9\xf5\xab.\xd7ba\x04\xbc\\Cr\x82s\xd3\xc9\xc5\xf2\xf7\xbe@SU\x0e\x1c.\xc2\x1e\xb3"3\xe5\x91\x96\xbd\xfd\xff\xee\x0e\xa7\xed\xb2Z\x89\xab\xd1\x13\xc5\xdb\r+\rs\xca\xd1\xc0I\x02\xa9;\xde\x82\xf7\xca\xb2\xb7(\x8e\xe4\x9b\xaa\xe22\xea\x12\r\xd0\x9d\x02\x11\x10-\x9a\x96\xb3;\xecZ\xf5\xb4K\xdb\xa0ys\x86z?`\x16\xca\xc6\xc6\x8c\x13\xcex\x81\xf1\xb3\xe5.L\xe8F\'\xd3\x05\x0c*\xe0\xf8\xf8U\x1fnc[|\xb7Tq\xc5\xb6\xeb\xe8\x03*\xcf@\xbf]\x80\xac\xe0\xc5w<\x99\xc9,\x93\xdc\xab\xa5|\x80O\xbd\xec\x0f\xb4\xbc}\xa4mh\xc2\xb5"x\xc7\xcc*\xb9\xd7xT7\xaf=\xb6sB\'X\xd4\xeb\xfe_\xd2\x1c+\x07R\xc1O\xca\xbf\xea]\xa9\xf1\xeb\xb1\x0b?%z\x7f\xdf\xe3\xc7=\xe8P\x8dB\xaf_E*8)\x1ae\x16\xff=-\xc3\x88e\x8ez\x96\xbb(\x8da\xac\x88\xbcU\xd7~l8\x0e\xc1\xb9j\xfda\x17axD\xa2\x1e\x0c\x98v\xc1\xd2X`\xba\x0c\xbfFM\x97\xe3\xcc\xb7\x91\x1a=\x87qm\xdfw\x9a;9\xf3\\f\x87\xa5\xd8\xff&t"\xcc\xdc\xfd\x87]\xbfe\x96\xa4\x9a\x15\tg\xb8\xca\x0b\x9c\xf9_]\xf7\xbc_'
	if'compress_data'in globals():raw_data=yaml.safe_load(zlib.decompress(compress_data));Kickback(raw_data).run()