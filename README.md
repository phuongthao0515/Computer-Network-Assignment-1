#A simple segment chat application (Discord-like)

## Introduction:
	This project implements a hybrid chat system combining the client-server and peer-to-peer (P2P) paradigms to efficiently broadcast data across a network of peers.

## Features:
- Hybrid chatting using both client-server and P2P techniques
- Peer registration via a central tracker, direct peer-to-peer broadcasting.
- User can choose to continue as guest or sign in/ sign up into an account. Account’s username is unique.
- Guests can join public channels, see the messages in those channel, but can’t send the message.
-	Authenticated users can join public channels and private channels that they have been accepted to join by the host. Sending message is allowed
-	Any visitors or authenticated users that have joined a channel can see the status (online/offline) of the authenticated users inside that channel
- Host of the channel can set the channel as public or private, and can grant the privillege 

## How to Run:
### 1. Start the Tracker (Central Server)
Run command:  
<pre lang="markdown"> ```Terminal
  # In Windows:
  python tracker.py 
  # In Linux:
  python3 tracker.py
 ``` </pre> 

2. Start the peer (host):
add command dô  
	
## System Architecture:
### Protocol:


## Possible errors:
- Authentication-relate errors: wrong username or password, user 
- Connection Failed
- Data Loss: due to network instability (chắc ko có phần bị concatenate hay gửi nửa, chỗ này handle r mà đúng hem)
- Port Binding:	assign host at the same port (do mình đang sài local host?)

## Note:
