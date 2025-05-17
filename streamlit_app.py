import streamlit as st
import pandas as pd
import sqlite3
import random
import string

# ---------- DATABASE SETUP ----------
def create_db():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, passcode INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS flights (flight_id INTEGER PRIMARY KEY, flight_number TEXT, status TEXT, assigned_user_id INTEGER)''')
    conn.commit()
    conn.close()

create_db()

# ---------- DATABASE HELPERS ----------
def get_users():
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return users

def add_user(name, passcode):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (name, passcode) VALUES (?, ?)", (name, passcode))
    conn.commit()
    conn.close()

def add_flight(flight_number):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("INSERT INTO flights (flight_number, status) VALUES (?, 'unallocated')", (flight_number,))
    conn.commit()
    conn.close()

def allocate_flight(flight_id, user_id):
    conn = sqlite3.connect('task_allocation.db')
    c = conn.cursor()
    c.execute("UPDATE flights SET status='allocated', assigned_user_id=? WHERE flight_id=?", (user_id, flight_id))
    conn.commit()
    conn.close
