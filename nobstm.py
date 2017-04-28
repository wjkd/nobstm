#!/usr/bin/python3

#############################################################
#                                                           #
# NO BULLSH*T TILING MANAGER                                #
# Automatically tiles windows for wms without native tiling #
# Built for openbox and lxde                                #
#                                                           #
#############################################################

from subprocess import check_output, run, CalledProcessError
import re
import time
import os.path

SCREEN_REGEX = r'^\s+dimensions:\s+(\d+)x(\d+)'
WINDOW_LIST_REGEX = r'^(0x\w+)\s+(\-?\d+)(?:\s+\d+){4}\s+\w+\s+(\w+)'

EXCLUDE = { # exclude tiling these
	'dockx' : False
}

VERTICAL_PADDING = 10
BOTTOM_PADDING = 40
TOP_PADDING = 15
LAST_BOTTOM_PADDING = 70

class Leaf(object):
	
	dict = {}
	
	def __init__(self, id):
		self.id = id
		self.parent = None
		self.direction = -1 # left: 0, right: 1
		
		Leaf.dict[id] = self
	
	# binary tree functions
	def remove(self):
		print(self, self.direction, self.parent)
		self.parent.remove(self.direction)
		del Leaf.dict[self.id]
	
	def swap(self, leaf):
		Lp, Sp = leaf.parent, self.parent
		if self.direction == 0:
			self.parent.left = leaf
		elif self.direction == 1:
			self.parent.right = leaf
		leaf.parent = Sp
		
		if leaf.direction == 0:
			leaf.parent.left = self
		elif leaf.direction == 1:
			leaf.parent.right = self
		self.parent = Lp
	
	# materialize
	def draw(self):
		run([ 'xdotool', 'windowsize', str(self.id), str(self.width), str(self.height) ])
		run([ 'xdotool', 'windowmove', str(self.id), str(self.x), str(self.y) ])
	
	def calculate_dimensions(self, width, height, vertical=True, x=0, y=0, max_height=None):
		self.width = width - VERTICAL_PADDING*2
		self.height = height - BOTTOM_PADDING
		
		self.x = x + VERTICAL_PADDING
		self.y = y + TOP_PADDING
		
		if self.y + self.height > max_height:
			self.height = max_height - self.y
	
	# string
	def __str__(self, indent=0):
		return ('\t'*indent) + '[' + str(self.id) + ']'
	

class Node(object):

	def __init__(self, left=None, right=None):
		self.left = left
		self.right = right
		
		if self.left:
			self.left.direction = 0
			self.left.parent = self
		if self.right:
			self.right.direction = 1
			self.right.parent = self
		
		self.parent = None
		self.direction = -1 # left: 0, right: 1
	
	# binary tree functions
	def remove(self, direction):
		if direction == -1:
			raise Exception('direction is -1')
		elif direction == 0:
			remainder = self.right
		else:
			remainder = self.left
		
		if isinstance(remainder, Node): # move other left and right tree up one
			print('NODE')
			
			self.left = remainder.left
			self.left.direction = 0
			self.left.parent = self
			
			self.right = remainder.right
			if self.right:
				self.right.direction = 1
				self.right.parent = self
			
		elif isinstance(remainder, Leaf):
			if self.parent == None:
				if direction == 0:
					self.left = self.right
					self.left.direction = 0
					self.right = None
				else:
					self.right = None
			else:
				#print('LEAFY',self.parent, self.parent.left)
				parent_direction = self.parent.direction
				#print('direction: ',parent_direction)
				if parent_direction == 1:
					self.parent.left = remainder
					remainder.direction = 0
				else:
					self.parent.right = remainder
					remainder.direction = 1
				remainder.parent = self.parent
		
		else: # None (remove from top node)
			self.left = None
			self.right = None
	
	def auto_insert(self, node):
		if self.left is None:
			node.parent = self
			self.left = node
			node.direction = 0
		elif self.right is None:
			#print(node,'n')
			node.parent = self
			self.right = node
			node.direction = 1
		else:
			#print('y')
			previous = self.right
			#previous.direction
			#node.direction
			self.right = Node(previous, node)
			#node.parent = self.right
			#previous.parent = self.right
			self.right.parent = self
			self.right.direction = 1
	
	def search(self, key):
		pass
	
	def swap(self, node):
		P1, P2 = self.parent, node.parent
		
		if self.direction == 0:
			self.parent.left = node
		else:
			self.parent.right = node
		node.parent = P1
		
		if node.direction == 0:
			node.parent.left = self
		else:
			node.parent.right = self
		self.parent = P2
	
	# materialize
	def draw(self):
		if self.left: self.left.draw()
		if self.right: self.right.draw()
	
	def calculate_dimensions(self, width, height, vertical=True, x=0, y=0, max_height=None):
		if self.left is None:
			return
		
		self.width = width
		self.height = height
		
		if vertical:
			if self.right:
				width /= 2
			
			self.left.calculate_dimensions(width, height, False, x, y, max_height)
			
			if self.right:
				self.right.calculate_dimensions(width, height, False, x + width, y, max_height)
		else:
			if self.right:
				height /= 2
			
			self.left.calculate_dimensions(width, height, True, x, y, max_height)
			
			if self.right:
				self.right.calculate_dimensions(width, height, True, x, y + height, max_height)
	
	def __str__(self, indent=0):
		return ('\t'*indent) + '{\n' + '\t\n'.join([
			(self.left.__str__(indent+1) if isinstance(self.left, Node) or isinstance(self.left, Leaf) else ('\t'*(indent+1)) + 'None') + ',',
			(self.right.__str__(indent+1) if isinstance(self.right, Node) or isinstance(self.right, Leaf) else ('\t'*(indent+1)) + 'None')
			#str(self.right)
		]) + '\n' + ('\t'*indent) + '}'

# screen shit
def make_window_tree(L):
	if not L:
		return Node()
	
	root = Node(Leaf(L[0]))
	L = L[1:]
	for value in L:
		root.auto_insert(Leaf(value))
	return root
	
def make_desktop_window_list():
	desktops = check_output(['wmctrl', '-d']).decode('utf-8').split('\n')
	desktop = next(filter(lambda line: re.search(r'^\d+\s+\*', line), desktops))
	desktop = int(re.match(r'^(\d+)', desktop).group(0))
	
	# get focused window title
	selected = int(check_output(['xdotool', 'getwindowfocus']).decode('utf-8').strip())
	selected_in = False
	
	windows_ = check_output(['wmctrl', '-lG']).decode('utf-8').split('\n')
	windows = []
	
	for line in windows_:
		matches = re.match(WINDOW_LIST_REGEX, line)
		if matches:
			i = int(matches.group(1), 16)
			if i == selected: # filter out selected
				selected_in = True
				continue
			if int(matches.group(2)) == desktop and matches.group(3) not in EXCLUDE:
				windows.append(i)
	
	# add selected as first priority
	if selected_in: # make sure it's not openbox and friends
		windows.insert(0, selected)
	
	print(windows)
	return (desktop, windows)

def track_changed_windows(desktop, old):
	windows_ = check_output(['wmctrl', '-lG']).decode('utf-8').split('\n')
	windows = []
	new = []
	cleared = []
	for line in windows_:
		matches = re.match(WINDOW_LIST_REGEX, line)
		if matches:
			i = int(matches.group(1), 16)
			#print(matches.group(3))
			if matches.group(3) in EXCLUDE and EXCLUDE[matches.group(3)]:
				EXCLUDE[matches.group(3)] = True
			if int(matches.group(2)) == desktop:
				if i not in old:
					print('new: ', i, old)
					new.append(i)
				windows.append(i)
				
	for i in old:
		if i not in windows:
			cleared.append(i)
			print('cleared',i,old)
	return (new, cleared)

def get_screen_size():
	lines = check_output(['xdpyinfo']).decode('utf-8').split('\n')
	line = next(filter(lambda line: 'dimensions' in line, lines))
	matches = re.match(SCREEN_REGEX, line)
	print(matches.group(1), matches.group(2))
	return (int(matches.group(1)), int(matches.group(2)))

# main
def main():
	check_requirements()
	
	desktop, windows = make_desktop_window_list()
	tree = make_window_tree(windows)
	width, height = get_screen_size()
	max_height = height - LAST_BOTTOM_PADDING
	
	tree.calculate_dimensions(width, height, max_height=max_height)
	print(tree)
	tree.draw()
	
	while True:
		try:
			new_windows, cleared_windows = track_changed_windows(desktop, Leaf.dict)
		except CalledProcessError:
			pass
		for window in new_windows:
			tree.auto_insert(Leaf(window))
			windows.append(window)
		for window in cleared_windows:
			if window in EXCLUDE:
				EXCLUDE[window] = False
			if window in windows:
				Leaf.dict[window].remove()
				windows[:] = (win for win in windows if win != window)
		if new_windows or cleared_windows:
			print(windows)
			print('update: ',tree)
			tree.calculate_dimensions(width, height, max_height=max_height)
			tree.draw()
		time.sleep(0.25)

def check_requirements():
	failed = False
	
	if not os.path.isfile('/usr/bin/xdotool'):
		print("You need to install xdotool!")
		failed = True
	
	if not os.path.isfile('/usr/bin/wmctrl'):
		print("You need to install wmctrl!")
		failed = True
	
	if failed:
		exit(0)

if __name__ == "__main__":
	main()
