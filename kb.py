G=True
F=KeyboardInterrupt
C=False
import termios as B,sys as D,struct as I,subprocess as J,fcntl
class E:FG_Black=30;FG_Red=31;FG_Green=32;FG_Yellow=33;FG_Blue=34;FG_Magenta=35;FG_Cyan=36;FG_White=37;Reset=0;BG_Black=40;BG_Red=41;BG_Green=42;BG_Yellow=43;BG_Blue=44;BG_Magenta=45;BG_Cyan=46;BG_White=47
class A:
 def setpos(B=1,col=1):
  if B==1 and col==1:return A.ESCAPE_STR+'H'
  return'%s%d;%dH'%(A.ESCAPE_STR,B,col)
 ESCAPE_STR='\x1b[';CLEAN=ESCAPE_STR+'2J';UP=ESCAPE_STR+'A';DOWN=ESCAPE_STR+'B';RIGHT=ESCAPE_STR+'C';LEFT=ESCAPE_STR+'D';CLEAN_SET=CLEAN+ESCAPE_STR+'H';ARROW=[UP,DOWN,RIGHT,LEFT]
class H:
 DIR={A.UP:(0,-1),A.DOWN:(0,1),A.RIGHT:(1,0),A.LEFT:(-1,0)}
 def init_termios(C):F='HHHH';E=D.stdin.fileno();C.old_settings=B.tcgetattr(E);A=B.tcgetattr(E);A[3]&=~(B.ICRNL|B.IXON);A[3]&=~ B.OPOST;A[3]&=~(B.ICANON|B.ECHO|B.IGNBRK|B.BRKINT);B.tcsetattr(E,B.TCSAFLUSH,A);G=I.pack(F,0,0,0,0);H=fcntl.ioctl(D.stdout.fileno(),B.TIOCGWINSZ,G);C.row,C.col,J,J=I.unpack(F,H)
 def __init__(B):B.init_termios();B.running=G;B.x=1;B.y=1;B.x_range=1,B.col;B.y_range=1,B.row;B.send(A.CLEAN)
 def send(A,buf):D.stdout.write(buf);D.stdout.flush()
 def send_color(B,buf,color):C='%s%dm%s%s%dm'%(A.ESCAPE_STR,color,buf,A.ESCAPE_STR,E.Reset);B.send(C)
 def send_color256(B,buf,color):C='%s48;5;%dm'(A.ESCAPE_STR,color,buf,A.ESCAPE_STR,E.Reset);B.send(C)
 def flushpos(B):B.send(A.setpos(B.y,B.x))
 def move(A,arrow):B=arrow;A.x=max(A.x_range[0],min(A.x+H.DIR[B][0],A.x_range[1]));A.y=max(A.y_range[0],min(A.y+H.DIR[B][1],A.y_range[1]));A.flushpos()
 def readchar(B):A=D.stdin.read(1);return A
 def readkey(B):
  A=B.readchar()
  if A in'\x03':raise F
  if A!='\x1b':return A
  C=B.readchar()
  if C not in'O[':return A+C
  D=B.readchar()
  if D not in'12356':return A+C+D
  E=B.readchar()
  if E not in'01345789':return A+C+D+E
  G=B.readchar();return A+C+D+E+G
 def key_event(C,key):
  B=key
  if B=='q':raise F
  elif B in A.ARROW:C.move(B)
 def display(A):0
 def run(A):
  while A.running:
   try:C=A.readkey();A.key_event(C)
   except F:B.tcsetattr(D.stdin,B.TCSADRAIN,A.old_settings);break
class K(H):
 bottom_msg='Tip: <Space> select. (S)tart script. Select (A)ll. (R)everse select. (q)uit'
 def __init__(A,menu_list):B=menu_list;super().__init__();A.menu_list=B;A.display();A.x,A.y=2,1;A.x_range=2,2;A.y_range=1,len(B);A.display()
 def key_event(B,key):
  C=key;super().key_event(C)
  if C==' ':E=B.y-1;B.menu_list[E][0]=not B.menu_list[E][0];B.send(A.setpos(B.y,1));B.set_line(B.menu_list[E]);B.flushpos()
  elif C=='S':
   if B.run_cmd():raise F
  elif C=='A':
   for D in B.menu_list:D[0]=G
   B.display()
  elif C=='R':
   for D in B.menu_list:D[0]=not D[0]
   B.display()
 def run_cmd(C):
  E=''
  for F in C.menu_list:
   if F[0]==G:E+=F[2]
  C.send(A.CLEAN_SET);B.tcsetattr(D.stdin,B.TCSADRAIN,C.old_settings);H=J.Popen(['/bin/bash','-c',E]);H.wait();return G
 def set_line(B,item):A=item;B.send('[%s] '%('v'if A[0]else' '));C=E.BG_Blue if A[0]else E.BG_Black;B.send_color('%s\r\n'%A[1],C)
 def display(B):
  B.send(A.CLEAN_SET)
  for C in B.menu_list:B.set_line(C)
  B.send(A.setpos(999,1));B.send(B.bottom_msg);B.flushpos()
if __name__=='__main__':L=[[C,'necessary','sudo apt install zsh clang make python3-pip curl docker.io ssh -y\n'],[C,'nodejs-16','curl -sSf https://deb.nodesource.com/setup_16.x | sudo sh\nsudo apt install nodejs -y\n'],[C,'rust','curl https://sh.rustup.rs -sSf | sh\n'],[C,'docker-compose','wget https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64\nchmod +x ./docker-compose-linux-x86_64\nsudo mv ./docker-compose-linux-x86_64 /bin/docker-compose\n'],[C,'nerdfont','wget https://github.com/ryanoasis/nerd-fonts/releases/latest/download/FiraCode.zip\nsudo unzip FiraCode -d /usr/share/fonts/FiraCode\ncd /usr/share/fonts/FiraCode\nsudo mkfontscale\nsudo mkfontdir\nsudo fc-cache -fv\n'],[C,'codeql',"latest_release=$(curl -Ls -o /dev/null -w %{url_effective}  \\\n  https://github.com/github/codeql-cli-binaries/releases/latest | cut -d'/' -f8)\nmkdir -p ~/cql\ncd ~/cql\nwget https://github.com/github/codeql-cli-binaries/releases/download/$latest_release/codeql-linux64.zip\nwget https://github.com/github/codeql/archive/refs/tags/codeql-cli/$latest_release.zip\nunzip codeql-linux64.zip $latest_release.zip\nmv codeql codeql-cli\nmv codeql-codeql-cli-$latest_release codeql-lib\nsudo ln -s ~/cql/codeql-cli/codeql /usr/bin/codeql\n"],[C,'neovim','sudo add-apt-repository ppa:neovim-ppa/stable -y\nsudo apt update\nsudo apt install neovim -y\n'],[C,'gef','bash -c "$(curl -fsSL https://gef.blah.cat/sh)"\n']];M=K(L);M.run()