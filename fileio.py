#!/usr/bin/python

#file io module

from utility import Instruction

#adding 3 operands to instructions
def add3(operands, instruction):
	instruction.dest_operand = str(operands[0])
	instruction.source_operand1 = str(operands[1])
	instruction.source_operand2 = str(operands[2])

def add2(operands, instruction):
	instruction.dest_operand = str(operands[0])
	instruction.source_operand1 = str(operands[1])

def add1(operands, instruction):
	instruction.dest_operand = str(operands[0])

#switcher
def insert_operands(n, operands, instruction):
	switcher = {
		3 : add3(operands, instruction),
		2 : add2(operands, instruction),
		1 : add1(operands, instruction)
	}

#loading instructions from the file
def read_from_file(filename):
	file_contents = []
	file_obj = open(filename, 'r')
	for line in file_obj:
		line_components = line.split()
		opcode = line_components[0]
		instruction = Instruction(opcode)
		if len(line_components[1:]) == 1:
			instruction.dest_operand = line_components[1]
		elif len(line_components[1:]) == 2:
			instruction.dest_operand = line_components[1]
			instruction.source_operand1 = line_components[2]
		elif len(line_components[1:]) == 3:
			instruction.dest_operand = line_components[1]
			instruction.source_operand1 = line_components[2]
			instruction.source_operand2 = line_components[3]
		file_contents.append(instruction)
	file_obj.close()
	return file_contents