### AI Server

- Adjust the "Force Train" function to limit the number of data pulls to prevent the system from freezing if there is a large queue. Implement periodic file saving.
    
- If a previously detected face is found within 5 minutes, do not save it to the database; instead, return a message stating that the student has already registered.
    

### App

- Adjust and support UI display for status checking, ensuring that both cases—where no pending data is found and where data is completed—are displayed beautifully.
    
- Adjust post-upload image verification to show users which photos passed and which failed, allowing them to fix the failed ones.
    
- During the capture process, include prompts for each photo (e.g., asking if the user is wearing glasses and requesting they remove them, or asking for facial expressions like smiling) to improve training efficiency. However, if you believe this is not significantly impactful or could lead to inaccuracies in the learning process, then this part is unnecessary.
    

### Web

- Adjust the queue table to group photos with the same ID into a dropdown menu, allowing users to click to view individual photos instead of viewing all of them at once, as the number of photos is high.