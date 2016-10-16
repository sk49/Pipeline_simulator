#!/usr/bin/python

#circular queue
from constants import *

class CQueue:
	def __init__(self, capacity):
		if capacity == -1:
			self.size = ROB_CAPACITY
		else:
			self.size = capacity
		self.entries = []		
		self.head = 0
		self.tail = 0

	def get_size(self):
		if self.tail > self.head:
			return self.tail - self.head
		else:
			return self.size - self.head + self.tail

	def is_empty(self):
		return self.tail == self.head

	def is_full(self):
		diff = self.tail - self.head
		if diff == -1 or diff == (self.size - 1):
			return True
		return False

	def enqueue(self, rob_entry):
		self.entries.append(rob_entry)
		self.tail = (self.tail + 1) % self.size

	def dequeue(self):
		item = self.entries[self.head]
		self.entries[self.head] = None
		self.head = (self.head + 1) % self.size
		return item

	def __str__(self):
		pass