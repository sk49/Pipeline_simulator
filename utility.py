#!/usr/bin/python

#utility module

from enum import Enum
from collections import defaultdict
from collections import deque

#reorder buffer entry
'''
itype -- instruction type
pc -- program counter
dest_addr -- string destination address
opcode -- string opcode
result -- RFileContents object
status_bit -- boolean bit
'''
class ROBEntry:
	def __init__(self, itype, pc, dest_addr, opcode,
		result, status_bit):
		self.itype = itype
		self.program_counter = pc
		self.dest_addr = dest_addr
		self.opcode = opcode
		self.result = result
		self.status_bit = status_bit

# #reorder buffer that stores ROBEntries
# rob = deque()

#register file contents
class RFileContents:
	def __init__(self, value, finishing_cycle):
		self.value = value
		self.finishing_cycle = finishing_cycle

# #register file
# register_file = defaultdict(RFileContents)
# regsister_set = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]
# for i in range(8):
# 	register_file[regsister_set[i]] = RFileContents(i,0)
# register_file["X"] = RFileContents(0,float('inf'))

# #memory
# memory = defaultdict(int)
# for i in range(10000):
# 	memory[str(i)] = 0

#rename table entry
class RenameTableEntry:
	def __init__(self, value, source_bit):
		self.value = value
		self.source_bit = source_bit

# #rename table map with the values as RenameTableEntry
# rename_table = defaultdict(RenameTableEntry)
# for register in regsister_set:
# 	rename_table[register] = RenameTableEntry(register, 0)

# #issue queue and laod store queue
# issue_queue = []
# load_store_queue = []

#register instructions list
register_instructions = [
	"ADD", "SUB", "MOV",
	"MOVC", "MUL", "AND",
	"OR", "XOR"
]

#memory instructions list
memory_instructions = [
	"LOAD", "STORE"
]

#branch instructions list
branch_instructions = [
	"BZ", "BNZ", "JUMP",
	"BAL", "HALT", "NOP"
]

#class to store instruction types
class IType(Enum):
	mem = 1
	reg = 2
	br = 3

	#determine the type of the instruction
	@staticmethod
	def getType(opcode):
		if opcode in register_instructions:
			return IType.reg
		elif opcode in memory_instructions:
			return IType.mem
		else:
			return IType.br

#class to store information pertaining to an instruction
class Instruction:
	# def __init__(self,opcode):
	# 	self.opcode = opcode
	# 	self.itype = IType.getType(opcode)
	# 	self.initializeRest()

	def __init__(self, opcode):
		self.opcode = opcode
		self.itype = IType.getType(opcode)
		self.program_counter = 0
		self.dest_operand = None
		self.source_operand1 = None
		self.source_operand2 = None
		self.source1_value = None
		self.source2_value = None
		self.dest_value = None
		self.literal = None
		self.mem_contents = None
		self.source1_decoded, self.source2_decoded, self.dest_decoded = False, False, False
		self.functional_unit = ""
		# if len(args) == 1:
		# 	self.source_operand1 = args[0]
		# elif len(args) == 2:
		# 	self.source_operand1 = args[0]
		# 	self.source_operand2 = args[1]

	# def __init__(self, opcode, sop1, sop2):
	# 	self.opcode = opcode
	# 	self.itype = IType.getType(opcode)
	# 	self.source_operand1 = sop1
	# 	self.source_operand2 = sop2
	# 	self.initializeRest()

	#check if operand is literal
	@staticmethod
	def isLiteral(operand):
		if operand[:1] != 'R':
			return True
		return False

	#retrieve information of stage
	def get_stage_information(self):
		information = str(self.program_counter) + ':' + self.opcode + ' '
		if self.dest_operand:
			if self.dest_value:
				information += str(self.dest_value)
			else:
				information += self.dest_operand
		if self.source_operand1:
			if self.source1_value:
				information += (',' + str(self.source1_value))
			else:
				information += (',' + self.source_operand1)
		if self.source_operand2:
			if self.source2_value:
				information += (',' + str(self.source2_value))
			else:
				information += (',') + self.source_operand2
		return information

	#tostring
	def __str__(self):
		return str(self.program_counter)

	#equals
	def __eq__(self, other):
		return isinstance(other, self.__class__) and (self.__dict__ == other.__dict__)