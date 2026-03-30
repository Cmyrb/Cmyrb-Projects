import http.server      
import json             
import random           
import urllib.parse     
import threading        
import webbrowser

game_state = {
    "balance": 500,          # Player starts with $500 each session
    "player_hand": [],       # Cards currently in the player's hand
    "dealer_hand": [],       # Cards currently in the dealer's hand
    "deck": [],              
    "game_active": False,    
    "message": "",           
    "can_split": False,      
    "split_hand": [],        
    "split_active": False,   
    "current_bet": 0,        
    "split_bet": 0,          
    "doubled_down": False,   