#!/usr/bin/python

#executor module.

from utility import ROBEntry
from utility import RFileContents
from utility import RenameTableEntry
from utility import IType
from utility import Instruction

from cqueue import CQueue

import fileio

from collections import OrderedDict
from collections import deque

from constants import *

import sys

#globals
pc = 20000
current_pc = pc
latest_pc = 0
list_of_instructions = []
pc_to_instruction_map = {}
can_halt = False
arithmetic_pipeline = list(list())
stage_pipeline = list(list())
cycle = 0
stage = 0
cycles_to_simulate = 0

#reorder buffer that stores ROBEntries
rob = None

def initialize_rob():
	global rob
	rob = CQueue(-1)

#register file
register_file = OrderedDict()

def initialize_rfile():
	global register_file
	register_set = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]
	for i in range(8):
		register_file[register_set[i]] = RFileContents(0,0)
	register_file["X"] = RFileContents(0,99999)

#memory
memory = OrderedDict()

def initialize_mem():
	global memory
	for i in range(10000):
		memory[str(i)] = 0

#rename table map with the values as RenameTableEntry
rename_table = OrderedDict()

def initialize_rt():
	global rename_table
	register_set = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]
	for register in register_set:
		rename_table[register] = RenameTableEntry(register, 0)

#issue queue and laod store queue
issue_queue = []
load_store_queue = []

#determine functional unit
def determine_functional_unit(opcode, categ1, categ2, instr):
	if opcode in categ1:
		instr.functional_unit = "Int"
	elif opcode in categ2:
		instr.functional_unit = "Mem"
	elif opcode == "MUL":
		instr.functional_unit = "Mul"

#initialize everything
def initialize():
	global current_pc
	global cycles
	global can_halt
	global latest_pc
	global list_of_instructions

	initialize_instruction()
	current_pc = pc
	cycle = 0
	can_halt = False
	latest_pc = list_of_instructions[len(list_of_instructions)-1].program_counter
	initialize_rfile()
	initialize_mem()
	initialize_rt()
	initialize_rob()

#initialize state
def initialize_instruction():
	global list_of_instructions
	
	temp_pc = pc
	for i in range(len(list_of_instructions)):
		list_of_instructions[i].program_counter = temp_pc
		temp_pc+=1

		#checking for instruction type and associating functional units
		determine_functional_unit(
				list_of_instructions[i].opcode,
				[   
					"ADD", "SUB", "AND"
					"OR", "XOR", "MOV",
					"MOVC", "JUMP", "HALT",
					"BAL", "BNZ", "BZ", "NOP"
				],
				["LOAD", "STORE"],
				list_of_instructions[i]
				)

		pc_to_instruction_map[list_of_instructions[i].program_counter] = list_of_instructions[i]

#initialize instruction
def nullify(instruction):
	instruction.dest_value = None
	instruction.source1_value = None
	instruction.source2_value = None
	instruction.mem_contents = None
	instruction.literal = None
	instruction.source1_decoded = None
	instruction.source2_decoded = None

def add_nop():
	global list_of_instructions

	nop_instr = Instruction("NOP")
	last_pc = ""
	for k,v in pc_to_instruction_map.items():
		last_pc = k
	nop_instr.program_counter = last_pc + 1
	nop_instr.source_operand1 = ""
	nop_instr.source_operand2 = ""
	nop_instr.dest_operand = ""
	pc_to_instruction_map[last_pc] = nop_instr


#simulate the executions of the instructions
#would have set cycles_to_simulate
def simulate(number_of_cycles_to_simulate):
	global cycle
	global stage
	global can_halt
	global current_pc
	global pc_to_instruction_map
	global cycles_to_simulate

	cycles_to_simulate = number_of_cycles_to_simulate

	for i in range(PIPELINE1_STAGES):
		arithmetic_pipeline.append(list())
		for j in range(number_of_cycles_to_simulate):
			arithmetic_pipeline[i].append(None)

	for i in range(PIPELINE2_STAGES):
		stage_pipeline.append(list())
		for j in range(number_of_cycles_to_simulate):
			stage_pipeline[i].append(None)

	has_next_instruction = True

	if len(pc_to_instruction_map) < cycles_to_simulate:
		for i in range(cycles_to_simulate):
			add_nop()

	while (has_next_instruction and (cycle < cycles_to_simulate)) and can_halt == False:
		if current_pc not in pc_to_instruction_map:
			break
		
		#initializing the instruction
		current_instruction = pc_to_instruction_map[current_pc]
		nullify(current_instruction)
		fetch1(current_instruction, cycle)
		current_pc += 1
		cycle += 1
		stage = 0

		if current_pc > latest_pc:
			has_next_instruction = False

	while (cycle+4) < cycles_to_simulate:
		issue_queue_operation(None, cycle + 4)
		cycle += 1

#update helper
def update_helper1(rob_entry):
	global register_file
	global rename_table
	global stage

	register_file[rob_entry.dest_addr] = rob_entry.result
	rename_table_entry = rename_table[rob_entry.dest_addr]
	rename_table_entry.source_bit = 0
	rename_table_entry.value = rob_entry.dest_addr
	rename_table[rob_entry.dest_addr] = rename_table_entry

#update helper
def update_helper2(rob_entry):
	global memory
	global register_file
	global stage

	memory[str(rob_entry.result.value)] = register_file[rob_entry.dest_addr].value

#update helper wrapper
def update_wrapper(rob_entry, opcode, categ1, categ2, categ3):
	if opcode in categ1:
		update_helper1(rob_entry)
	elif opcode in categ2:
		update_helper2(rob_entry)
	else:
		return

#updating processor state
def update_processor_state(current_cycle):
	global rob
	global stage

	while True:
		if not rob.is_empty():
			#retrieving element from the head of the queue
			rob_entry = rob.entries[rob.head]
			#rob_entry = list(rob)[0]
			if rob_entry.result.finishing_cycle < (current_cycle-1):
				update_wrapper(
						rob_entry, rob_entry.opcode,
						[
							"ADD", "SUB", "MUL",
							"AND", "OR", "XOR",
							"MOV", "MOVC", "LOAD"
						],
						["STORE"],
						[
							"JUMP", "HALT", "BAL",
							"BNZ", "BZ", "NOP"
						]
					)
				#rob.popleft()
				rob.dequeue()
			else:
				break
		else:
			break

#fetch stage 1
def fetch1(instruction, current_cycle):
	global arithmetic_pipeline
	global stage

	if arithmetic_pipeline[stage][current_cycle] == None:
		arithmetic_pipeline[stage][current_cycle] = instruction.get_stage_information()
	fetch2(instruction, current_cycle)

#fetch stage 2
def fetch2(instruction, current_cycle):
	global stage
	global arithmetic_pipeline
	if ((current_cycle + 1) < cycles_to_simulate) and arithmetic_pipeline[stage+1][current_cycle+1] == None:
		stage += 1
		current_cycle += 1
		arithmetic_pipeline[stage][current_cycle] = instruction.get_stage_information()
		decode1(instruction, current_cycle)

#decode stage 1
def decode1(instruction, current_cycle):
	global cycles_to_simulate
	global arithmetic_pipeline
	global stage
	global can_halt
	if ((current_cycle + 1) < cycles_to_simulate) and arithmetic_pipeline[stage+1][current_cycle+1] == None:
		decode_operation1(instruction, current_cycle+1)
		stage += 1
		current_cycle += 1 
		arithmetic_pipeline[stage][current_cycle] = instruction.get_stage_information()

		if instruction.opcode != "HALT":
			decode2(instruction, current_cycle)
		elif instruction.opcode == "NOP":
			pass
		else:
			can_halt = True

#decode stage 2
def decode2(instruction, current_cycle):
	global cycles_to_simulate
	global can_halt
	global stage
	global issue_queue
	global load_store_queue
	global arithmetic_pipeline
	if ((current_cycle + 1) < cycles_to_simulate) and arithmetic_pipeline[stage+1][current_cycle+1] == None:
		decode_operation2(instruction, current_cycle + 1)
		stage += 1
		current_cycle += 1
		arithmetic_pipeline[stage][current_cycle] = instruction.get_stage_information()
		if instruction.itype == IType.reg:
			if len(issue_queue) < ISSUE_Q:
				issue_queue_stage(instruction, current_cycle)
			else:
				stall_pipeline()
				current_register_cycle = current_cycle
				while len(issue_queue) >= ISSUE_Q:
					issue_queue_operation(None, current_register_cycle)
					current_register_cycle += 1
				issue_queue_stage(instruction, current_register_cycle)
		elif instruction.itype == IType.mem:
			if len(load_store_queue) < LOAD_STORE_Q:
				issue_queue_stage(instruction, current_cycle)
			else:
				stall_pipeline()
				current_memory_cycle = current_cycle
				while len(load_store_queue) >= LOAD_STORE_Q:
					issue_queue_operation(None, current_memory_cycle)
					current_memory_cycle += 1
				issue_queue_stage(instruction, current_memory_cycle)


# stall the pipeline. Need to complete.
def stall_pipeline():
	pass

#decode operation 1. Handling branch instructions
def decode_operation1(instruction, current_cycle):
	global cycles_to_simulate
	global register_file
	global stage
	if instruction.itype == IType.br:
		if instruction.opcode == "HALT":
			if cycles_to_simulate > (current_cycle + 4):
				cycles_to_simulate = current_cycle + 4
		elif instruction.opcode == "JUMP":
			if instruction.dest_operand != None:
				if register_file[instruction.dest_operand].finishing_cycle <= current_cycle:
					instruction.dest_value = register_file[instruction.dest_operand].value
					instruction.dest_decoded = True
			instruction.source1_value = int(instruction.source_operand1)
			instruction.source1_decoded = True
		elif instruction.opcode == "BAL":
			if instruction.dest_operand != None:
				if register_file[instruction.dest_operand].finishing_cycle <= current_cycle:
					instruction.dest_value = register_file[instruction.dest_operand].value
					instruction.dest_decoded = True
			instruction.source1_value = int(instruction.source_operand1)
			instruction.source1_decoded = True
		elif instruction.opcode == "BNZ" or instruction.opcode == "BZ":
			if instruction.dest_operand != None:
				instruction.dest_value = int(instruction.dest_operand)
				instruction.dest_decoded = True
		elif instruction.opcode == "NOP":
			instruction.dest_decoded = True
			pass
#decode operation 2. Handling arithmetic and load store instructions.
def decode_operation2(instruction, current_cycle):
	global rob
	global rename_table
	global stage
	decode_instruction(instruction, current_cycle)
	categ1 = ["ADD", "SUB", "MUL", "AND", "OR", "XOR", "LOAD", "MOV", "MOVC"]
	categ2 = ["STORE"]
	if instruction.opcode in categ1:
		#checking if reorder buffer is full
		if not rob.is_full():
		#if len(rob) < ROB_CAPACITY:
			rob_entry = ROBEntry(instruction.itype, instruction.program_counter,
				instruction.dest_operand, instruction.opcode, RFileContents(0,99999), False)
			#adding entry to reorder buffer
			rob.enqueue(rob_entry)
			#rob.append(rob_entry)
			rename_table_entry = rename_table[instruction.dest_operand]
			rename_table_entry.source_bit = 1
			#rename_table_entry.value = str(len(rob) - 1)
			rename_table_entry.value = str(rob.get_size() - 1)
			rename_table[instruction.dest_operand] = rename_table_entry
		else:
			return
	elif instruction.opcode in categ2:
		if not rob.is_full():
		#if len(rob) < ROB_CAPACITY:
			rob_entry = ROBEntry(instruction.itype, instruction.program_counter,
				instruction.dest_operand, instruction.opcode, RFileContents(0,99999), False)
			#rob.append(rob_entry)
			rob.enqueue(rob_entry)
		else:
			return
	else:
		return

#decoding the instruction
def decode_instruction(instruction, current_cycle):
	global rename_table
	global register_file
	global rob
	global stage
	categ1 = ["ADD", "SUB", "MUL", "AND", "OR", "XOR", "LOAD"]
	if instruction.opcode in categ1:
		#checking whether source operand 1 is a literal
		if instruction.source_operand1[:1] != "R":
			instruction.source1_value = int(instruction.source_operand1)
			instruction.source1_decoded = True
		else:
			source1_rt_entry = rename_table[instruction.source_operand1]
			if source1_rt_entry.source_bit == 0:
				instruction.source1_value = register_file[source1_rt_entry.value].value
				instruction.source1_decoded = True
			else:
				if rob.entries[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.source1_value = rob.entries[int(source1_rt_entry.value)].result.value
					#instruction.source1_value = list(rob)[int(source1_rt_entry.value)].result.value
					instruction.source1_decoded = True
		#checking whether source operand 2 is a literal
		if instruction.source_operand2[:1] != "R":
			instruction.source2_value = int(instruction.source_operand2)
			instruction.source2_decoded = True
		else:
			source2_rt_entry = rename_table[instruction.source_operand2]
			if source2_rt_entry.source_bit == 0:
				instruction.source2_value = register_file[source2_rt_entry.value].value
				instruction.source2_decoded = True
			else:
				if rob.entries[int(source2_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(source2_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.source2_value = rob.entries[int(source2_rt_entry.value)].result.value
					#instruction.source2_value = list(rob)[int(source2_rt_entry.value)].result.value
					instruction.source2_decoded = True
	elif instruction.opcode == "MOV" or instruction.opcode == "MOVC":
		if instruction.source_operand1[:1] != "R":
			instruction.source1_value = int(instruction.source_operand1)
			instruction.source1_decoded = True
		else:
			source1_rt_entry = rename_table[instruction.source_operand1]
			if source1_rt_entry.source_bit == 0:
				instruction.source1_value = register_file[source1_rt_entry.value].value
				instruction.source1_decoded = True
			else:
				if rob.entries[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.source1_value = rob.entries[int(source1_rt_entry.value)].result.value
					#instruction.source1_value = list(rob)[int(source1_rt_entry.value)].result.value
					instruction.source1_decoded = True
	elif instruction.opcode == "STORE":
		#checking if destination operand is a literal
		if instruction.dest_operand[:1] != "R":
			instruction.dest_value = int(instruction.dest_operand)
			instruction.dest_decoded = True
		else:
			dest_rt_entry = rename_table[instruction.dest_operand]
			if dest_rt_entry.source_bit == 0:
				instruction.dest_value = register_file[dest_rt_entry.value].value
				instruction.dest_decoded = True
			else:
				if rob.entries[int(dest_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(dest_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.dest_value = rob.entries[int(dest_rt_entry.value)].result.value
					#instruction.dest_value = list(rob)[int(dest_rt_entry.value)].result.value
					instruction.dest_decoded = True
		#checking if source1 operand is a literal
		if instruction.source_operand1[:1] != "R":
			instruction.source1_value = int(instruction.source_operand1)
			instruction.source1_decoded = True
		else:
			source1_rt_entry = rename_table[instruction.source_operand1]
			if source1_rt_entry.source_bit == 0:
				instruction.source1_value = register_file[source1_rt_entry.value].value
				instruction.source1_decoded = True
			else:
				if rob.entries[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(source1_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.source1_value = rob.entries[int(source1_rt_entry.value)].result.value
					#instruction.source1_value = list(rob)[int(source1_rt_entry.value)].result.value
					instruction.source1_decoded = True
		#checking if source2 operand is a literal
		if instruction.source_operand2[:1] != "R":
			instruction.source2_value = int(instruction.source_operand2)
			instruction.source2_decoded = True
		else:
			source2_rt_entry = rename_table[instruction.source_operand2]
			if source2_rt_entry.source_bit == 0:
				instruction.source2_value = register_file[source2_rt_entry.value].value
				instruction.source2_decoded = True
			else:
				if rob.entries[int(source2_rt_entry.value)].result.finishing_cycle < current_cycle:
				#if list(rob)[int(source2_rt_entry.value)].result.finishing_cycle < current_cycle:
					instruction.source1_value = rob.entries[int(source2_rt_entry.value)].result.value
					#instruction.source1_value = list(rob)[int(source1_rt_entry.value)].result.value
					instruction.source1_decoded = True
	else:
		return

#issue queue stage
def issue_queue_stage(instruction, current_cycle):
	global cycles_to_simulate
	global arithmetic_pipeline
	global stage
	if ((current_cycle + 1) < cycles_to_simulate) and arithmetic_pipeline[stage+1][current_cycle+1] == None:
		stage += 1
		current_cycle += 1
		arithmetic_pipeline[stage][current_cycle] = instruction.get_stage_information()
		issue_queue_operation(instruction, current_cycle)

#resolving dependencies
def resolve_dependencies(current_cycle):
	global issue_queue
	global load_store_queue
	global stage
	#just need to decode the instructions in the issue queue and the load store queue
	for instr in issue_queue:
		decode_instruction(instr, current_cycle)
	for instr in load_store_queue:
		decode_instruction(instr, current_cycle)

#issue queue operation
def issue_queue_operation(instruction, current_cycle):
	global issue_queue
	global load_store_queue
	global stage
	update_processor_state(current_cycle)
	resolve_dependencies(current_cycle)
	available_instructions = retrieve_available_instructions()
	next_int_instruction = get_next_int_instruction(available_instructions)
	next_mem_instruction = get_next_mem_instruction(available_instructions)
	next_mul_instruction = get_next_mul_instruction(available_instructions, current_cycle)

	if next_int_instruction != None:
		execute_stage(next_int_instruction, current_cycle)
		update_issue_queue(next_int_instruction)

	if next_mul_instruction != None:
		execute_stage(next_mul_instruction, current_cycle)
		update_issue_queue(next_mul_instruction)

	if next_mem_instruction != None:
		execute_stage(next_mem_instruction, current_cycle)
		update_load_store_queue(next_mem_instruction)

	if instruction != None:
		if instruction.itype == IType.reg or instruction.itype == IType.br:
			if len(issue_queue) < ISSUE_Q:
				issue_queue.append(instruction)
		elif instruction.itype == IType.mem:
			if len(load_store_queue) < LOAD_STORE_Q:
				load_store_queue.append(instruction)

#execute stage
def execute_stage(instruction, current_cycle):
	global cycles_to_simulate
	global stage_pipeline
	global arithmetic_pipeline
	global rob
	global stage
	if instruction.functional_unit == "Int":
		if (current_cycle < cycles_to_simulate) and arithmetic_pipeline[INT_STAGE][current_cycle] == None:
			stage_pipeline[INT_STAGE][current_cycle] = instruction.get_stage_information()
			execute_operation(instruction, current_cycle)
			update_rob(instruction, current_cycle)
		elif instruction.functional_unit == "Mul":
			current_mul_cycle = current_cycle
			while current_mul_cycle < (current_cycle + 4):
				if (current_mul_cycle < cycles_to_simulate) and arithmetic_pipeline[MUL_STAGE][current_mul_cycle] == None:
					stage_pipeline[MUL_STAGE][current_mul_cycle] = instruction.get_stage_information()
					current_mul_cycle += 1
				else:
					break
			if (current_mul_cycle - 1) == (current_cycle + 3):
				execute_operation(instruction, current_cycle)
				update_rob(instruction, (current_mul_cycle - 1))
		elif instruction.functional_unit == "Mem":
			temp_mem_stage = MEM_STAGE
			current_mem_cycle = current_cycle
			while temp_mem_stage < len(stage_pipeline):
				if (current_mem_cycle < cycles_to_simulate) and arithmetic_pipeline[temp_mem_stage][current_mem_cycle] == None:
					stage_pipeline[temp_mem_stage][current_mem_cycle] = instruction.get_stage_information()
				temp_mem_stage += 1
				current_mem_cycle += 1

			if temp_mem_stage == len(stage_pipeline):
				execute_operation(instruction, current_cycle)
				update_rob(instruction, (current_mem_cycle - 1))

#execute instructions
def execute_operation(instruction, current_cycle):
	global current_pc
	global cycle
	global cycles_to_simulate
	global arithmetic_pipeline
	global stage_pipeline
	global pc_to_instruction_map
	global stage
	global can_halt
	global register_file
	if instruction.opcode == "ADD":
		instruction.dest_value = instruction.source1_value + instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "SUB":
		instruction.dest_value = instruction.source1_value - instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "MUL":
		instruction.dest_value = instruction.source1_value * instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "AND":
		instruction.dest_value = instruction.source1_value & instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "OR":
		instruction.dest_value = instruction.source1_value | instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "XOR":
		instruction.dest_value = instruction.source1_value ^ instruction.source2_value
		instruction.dest_decoded = True
	elif instruction.opcode == "MOV":
		instruction.dest_value = instruction.source1_value
		instruction.dest_decoded = True
	elif instruction.opcode == "MOVC":
		instruction.dest_value = instruction.source1_value
		instruction.dest_decoded = True
	elif instruction.opcode == "LOAD":
		instruction.literal = int(instruction.source1_value + instruction.source2_value)
		instruction.dest_decoded = True
	elif instruction.opcode == "STORE":
		instruction.literal = int(instruction.source1_value + instruction.source2_value)
		instruction.dest_decoded = True
	elif instruction.opcode == "JUMP":
		#need to check if instructions are available
		instruction.literal = int(instruction.dest_value + instruction.source1_value)
		if (current_pc + 1) not in pc_to_instruction_map:
			temp_instr = pc_to_instruction_map[current_pc + 1]
			temp_col = cycle + 1
			while (temp_col <= (current_cycle - 1)) and (temp_col < cycles_to_simulate):
				arithmetic_pipeline[stage - 2][temp_col] = temp_instr.get_stage_information()
				temp_col += 1
			decode_operation1(temp_instr, current_cycle)
			arithmetic_pipeline[stage - 1][current_cycle] = temp_instr.get_stage_information()
			if (current_pc + 2) not in pc_to_instruction_map:
				temp_intsr2 = pc_to_instruction_map[current_pc + 2]
				arithmetic_pipeline[stage - 2][current_cycle] = temp_instr2.get_stage_information()

		#updating current program counter and cycle
		current_pc = instruction.literal - 1
		cycle = current_cycle
	elif instruction.opcode == "HALT":
		can_halt = True
	elif instruction.opcode == "BAL":
		instruction.literal = int(instruction.dest_value + instruction.source1_value)
		register_file["X"] = RFileContents(current_pc + 1, current_cycle)
		if (current_pc + 1) not in pc_to_instruction_map:
			temp_instr = pc_to_instruction_map[current_pc + 1]
			temp_col = cycle + 1
			while (temp_col <= (current_cycle - 1)) and (temp_col < cycles_to_simulate):
				arithmetic_pipeline[stage - 2][temp_col] = temp_instr.get_stage_information()
				temp_col += 1
			decode_operation1(temp_instr, current_cycle)
			arithmetic_pipeline[stage - 1][current_cycle] = temp_instr.get_stage_information()
			if (current_pc + 2) not in pc_to_instruction_map:
				temp_instr2 = pc_to_instruction_map[current_pc + 2]
				arithmetic_pipeline[stage - 2][current_cycle] = temp_intsr2.get_stage_information()

		#updating current program counter and cycle
		current_pc = instruction.literal - 1
		cycle = current_cycle
	elif instruction.opcode == "BNZ":
		prev_instr = pc_to_instruction_map[current_pc - 1]
		if register_file[prev_instr.dest_operand].value != 0:
			if (current_pc + 1) not in pc_to_instruction_map:
				temp_instr = pc_to_instruction_map[current_pc + 1]
				temp_col = cycle + 1
				while (temp_col <= (current_cycle - 1)) and (temp_col < cycles_to_simulate):
					arithmetic_pipeline[stage - 2][temp_col] = temp_instr.get_stage_information()
					temp_col += 1
				decode_operation1(temp_instr, current_cycle)
				arithmetic_pipeline[stage - 1][current_cycle] = temp_instr.get_stage_information()
				if (current_pc + 2) not in pc_to_instruction_map:
					temp_instr2 = pc_to_instruction_map[current_pc + 2]
					arithmetic_pipeline[stage - 2][current_cycle] = temp_instr2.get_stage_information()

			#updating current program counter and cycle
			current_pc = (current_pc + instruction.dest_value) - 1
			cycle = current_cycle
	elif instruction.opcode == "BZ":
		prev_instr = pc_to_instruction_map[current_pc - 1]
		if register_file[prev_instr.dest_operand].value == 0:
			temp_instr = pc_to_instruction_map[current_pc + 1]
			temp_col = cycle + 1
			while (temp_col <= (current_cycle - 1)) and (temp_col < cycles_to_simulate):
				arithmetic_pipeline[stage - 2][temp_col] = temp_instr.get_stage_information()
				temp_col += 1
			decode_operation1(temp_instr, current_cycle)
			arithmetic_pipeline[stage - 1][current_cycle] = temp_instr.get_stage_information()
			if (current_pc + 2) not in pc_to_instruction_map:
				temp_instr2 = pc_to_instruction_map[current_pc + 2]
				arithmetic_pipeline[stage - 2][current_cycle] = temp_intsr2.get_stage_information()

		#updating current program counter and cycle
		current_pc = (current_pc + instruction.dest_value) - 1
		cycle = current_cycle
	elif instruction.opcode == "NOP":
		instruction.dest_decoded = True

#get the next int instruction
def get_next_int_instruction(available_instructions):
	for instr in available_instructions:
		if instr.functional_unit == "Int":
			return instr
	return None

#get the next mul instruction
def get_next_mul_instruction(available_instructions, current_cycle):
	global cycles_to_simulate
	global stage_pipeline
	global stage

	if ((current_cycle + 1) < cycles_to_simulate) and stage_pipeline[MUL_STAGE][current_cycle] == None:
		for instr in available_instructions:
			if instr.functional_unit == "Mul":
				return instr
	return None

#get the next mem instruction
def get_next_mem_instruction(available_instructions):
	global rob
	global stage

	for instr in available_instructions:
		if instr.functional_unit == "Mem":
			if instr.opcode == "STORE":
				if rob.entries[rob.head].program_counter == instr.program_counter:
				#if rob[0].program_counter == instruction.program_counter:
					return instr
				else:
					return None
			return instr
	return None

#retrieve available instructions
def retrieve_available_instructions():
	global issue_queue
	global load_store_queue
	global stage
	available_instructions = []
	for instr in issue_queue:
		if instr.opcode in ["ADD", "SUB", "MUL", "AND", "OR", "XOR"]:
			if instr.source1_decoded and instr.source2_decoded:
				available_instructions.append(instr)
		elif instr.opcode in ["MOV", "MOVC"]:
			if instr.source1_decoded:
				available_instructions.append(instr)

	for instr in load_store_queue:
		if instr.opcode == "LOAD":
			if instr.source1_decoded and instr.source2_decoded:
				available_instructions.append(instr)
		elif instr.opcode == "STORE":
			if instr.source1_decoded and instr.source2_decoded and instr.dest_decoded:
				available_instructions.append(instr)
	return available_instructions

#removing the entry from issue queue
def update_issue_queue(instruction):
	global issue_queue
	global stage
	issue_queue.remove(instruction)


#removing the entry from load store queue
def update_load_store_queue(instruction):
	global load_store_queue
	global stage
	load_store_queue.remove(instruction)

#updating reorder buffer
def update_rob(instruction, current_cycle):
	global rob
	global memory
	global stage
	if instruction.itype == IType.reg:
		rob_entry = rob.entries[int(rename_table[instruction.dest_operand].value)]
		#rob_entry = list(rob)[int(rename_table[instruction.dest_operand].value)]
		rob_entry.result = RFileContents(instruction.dest_value, current_cycle)
	elif instruction.opcode == "LOAD":
		rob_entry = rob.entries[int(rename_table[instruction.dest_operand].value)]
		#rob_entry = list(rob)[int(rename_table[instruction.dest_operand].value)]
		rob_entry.result = RFileContents(memory[str(instruction.literal)], current_cycle)
	elif instruction.opcode == "STORE":
		rob_entry = None
		for temp in rob.entries:
			if (temp != None) and (temp.program_counter == instruction.program_counter):
				rob_entry = temp
				break
		rob_entry.result = RFileContents(instruction.literal, current_cycle)

'''display functions'''

#diplay initialization
def display_init():
	global list_of_instructions
	global stage

	print("Instructions:")
	for instruction in list_of_instructions:
		to_be_printed = str(instruction.program_counter)+' '
		if instruction.dest_operand != None:
			to_be_printed += instruction.opcode + ' ' +instruction.dest_operand +' '
			if instruction.source_operand1 != None:
				to_be_printed += instruction.source_operand1 +' '
			if instruction.source_operand2 != None:
				to_be_printed += instruction.source_operand2 + ' '
		else:
			to_be_printed += instruction.opcode
		
		print(to_be_printed)
	display_rfile()
	display_mem()

#display register file
def display_rfile():
	global register_file
	global stage

	print("Register File Contents:")
	to_be_printed = ""
	for addr, value in register_file.items():
		to_be_printed += ' '.join(['[', str(addr), '=', str(value.value), ']\t'])
		#to_be_printed += '[ '+str(addr)+' = '+str(value.value)+' ]\t'
	print(to_be_printed)


#display memory
def display_mem():
	global memory
	global stage

	print("Memory Contents:")
	low, high = None, None

	for outer in range(10):
		low = outer * 10
		high = ((outer + 1) * 10) - 1
		to_be_printed = ""
		for count in range(low, high+1):
			to_be_printed += ' '.join(['[', str(count), ':', str(memory[str(count)]), ']'])
		print(to_be_printed)

#display rename_table
def display_rename_table():
	global rename_table
	global stage

	print("Rename Table:")
	for key,value in rename_table.items():
		to_be_printed = ' '.join([str(key), '[', str(value.value), '|', str(value.source_bit), ']'])
		print(to_be_printed)

#display rob
def display_rob():
	global rob
	global stage

	print("ROB:")
	to_be_printed = "["
	for rob_entry in rob.entries:
		if rob_entry != None:
			to_be_printed += str(rob_entry.program_counter) + ", "
	to_be_printed += ']'
	print(to_be_printed)

#display queues
def display_queues():
	print("Issue Queue:", end=' ')
	print("[ ", end=' ')
	for instruction in issue_queue:
		print(instruction, end=',')
	print(" ]")
	print()
	print("Load Store Queue:", end=' ')
	print("[ ", end=' ')
	for instruction in load_store_queue:
		print(instruction, end=',')
	print(" ]")
	print()

#display simulation
def display_simulation(number_of_cycles_to_display):
	print("Pipeline Status after "+str(number_of_cycles_to_display)+" cycles:")

	print(''.join(["Fetch1 --- [ ", str(get_from_arith_pipeline(0, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Fetch2 --- [ ", str(get_from_arith_pipeline(1, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Decode1 --- [ ", str(get_from_arith_pipeline(2, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Decode2 --- [ ", str(get_from_arith_pipeline(3, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Issue Queue --- [ ", str(get_from_arith_pipeline(4, number_of_cycles_to_display)), ' ]']))
	print()
	print(''.join(["Int FU -- [", str(get_from_stage_pipeline(INT_STAGE, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Mul FU -- [", str(get_from_stage_pipeline(MUL_STAGE, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Memory FU Stage1 -- [", str(get_from_stage_pipeline(MEM_STAGE, number_of_cycles_to_display)), ' ]']))	
	print(''.join(["Memory FU Stage2 -- [", str(get_from_stage_pipeline(MEM_STAGE+1, number_of_cycles_to_display)), ' ]']))
	print(''.join(["Memory FU Stage3 -- [", str(get_from_stage_pipeline(MEM_STAGE+2, number_of_cycles_to_display)), ' ]']))
	print()
	display_rfile()
	display_mem()
	display_rename_table()
	display_queues()
	display_rob()

#getting from arithmetic pipeline
def get_from_arith_pipeline(stage, number_of_cycles_to_display):
	if arithmetic_pipeline != None:
		if arithmetic_pipeline[stage][number_of_cycles_to_display-1] == None:
			return "No Instruction"
		else:
			return arithmetic_pipeline[stage][number_of_cycles_to_display-1]
	else:
		return ""

#getting from memory pipeline
def get_from_stage_pipeline(stage, number_of_cycles_to_display):
	if stage_pipeline != None:
		if stage_pipeline[stage][number_of_cycles_to_display-1] == None:
			return "No Instruction"
		else:
			return stage_pipeline[stage][number_of_cycles_to_display-1]
	else:
		return ""

def main():
	global list_of_instructions
	global cycles_to_simulate
	global stage

	number_of_cycles_to_simulate = 0
	exit = False
	while exit == False:
		print("Please enter the following commands")
		print("LOAD <filename>")
		print("INITIALIZE")
		print("SIMULATE <cycles>")
		print("DISPLAY")
		print("EXIT")

		user_input = input()
		user_input_components = user_input.split()
		if user_input_components[0].lower() == "load":
			filename = user_input_components[1]
			list_of_instructions = fileio.read_from_file(filename)
			number_of_cycles_to_simulate = 0
			print("File Loaded!")
		elif user_input_components[0].lower() == "initialize":
			initialize()
			display_init()
			number_of_cycles_to_simulate = 0
			print("Initialisation complete!")
		elif user_input_components[0].lower() == "simulate":
			number_of_cycles_to_simulate += int(user_input_components[1])
			simulate(number_of_cycles_to_simulate)
			print("Simulation complete!")
		elif user_input_components[0].lower() == "display":
			display_simulation(number_of_cycles_to_simulate)
		elif user_input_components[0].lower() == "exit":
			print("Done!")
			exit = True
		else:
			print("Please enter a valid command")




if __name__ == '__main__':
	main()
