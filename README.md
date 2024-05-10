# BOOKING TELEGRAM BOT

Booking Telegram Bot is a Python-based bot designed to assist users in creating information panels in chat with hotel 
options from Booking.com, tailored to their preferences. It utilizes the aiogram library for Telegram bot interactions, 
aiosqlite for database management and combination of Selenium and BeautifulSoup4 for data parsing.


## Video Demo
https://youtu.be/riZdR6BrTXw?si=iwXS9PmgaZRdGZfi

## Usage


### Quickstart

#### Step 1: Initiate the bot
Start by sending the `/start` command to your Booking Telegram Bot. This will provide you with a brief description of 
the bot's features and commands.

#### Step 2: Start the form
To create info panels, use the `/start_form` command. The bot will guide you through a series of questions to tailor the
hotel search to your preferences.

#### Step 3: Complete the form
- **Destination**: Enter the destination you're interested in, separated by commas if there are multiple.
- **Check-in and check-out dates**: Select your check-in and check-out dates. If you need additional dates, choose 'yes' when prompted.
- **Adults and children**: Specify the number of adults and children staying, including the ages of the children.
- **Sorting**: Choose your preferred sorting method for the search results from booking.com.

#### Step 4:
Wait for the bot to collect all the information about hotels from Booking.com. After that, it will generate multiple info panels containing:
- Photos of the hotels
- Descriptions including name, price, rating, destination, and dates
- Inline-keyboard buttons: `Link`, `Refresh`, `Delete`, `Show as list`, and navigation arrows


### Navigation

- **Arrows**: Navigate through the panel to view details and photos of each hotel.

- **Show as list**: Displays a list view of hotels with name, price, and rating.

- **Link**: Directs to the Booking.com page with the selected hotel's details.

- **Refresh**: Updates the info panel with the latest data.

- **Delete**: Removes the info panel from the database and the chat.


### Commands

- **/start**: Initiates the bot and provides a brief description of its features and commands.

- **/start_form**: Begins the process of creating a new info panel by filling out a form.

- **/cancel**: Cancels the form at any time and deletes related messages.

- **/refresh_all**: Refreshes all info panels with the latest data.

- **/delete_all**: Removes all info panels from the databse and the chat.

- **/get_excel**: Provides data of all hotels in Excel format, sorted by user preference.

- **/get_form**: Displays the details entered by the user:
    - adults
    - children
    - children's ages
    - sorting preferences


## Developer Notes


### Parsing
To collect hotel data from Booking.com, I've chosen Selenium WebDriver because the site is dynamic, meaning content 
changes when users interact with it. After using Selenium to reveal more hotels, I switch to Beautiful Soup to extract 
the hotel details. This is because Beautiful Soup is faster at processing the page’s information than Selenium.

 The Selenium WebDriver is configured to click the ‘Load More’ button only twice. This gives us a good number of hotels to 
choose from without waiting too long for the results. 

If you would like to change the amount of times parser clicks 'Load More' button, go to utils.constants.py and 
change the `LOAD_MORE_BUTTON_CLICKS` variable.


### Threading
If you want to change the maximum amount of workers for ThreadPoolExecutor go to utils.constants.py and change the 
`MAX_WORKERS` variable.


 ### Preventing Overuse
 I've set limits on the number of hotel panels the bot can create and how often the ‘Refresh’ button can be used. 
 This helps to keep the bot running smoothly for everyone. To adjust the number of hotel panels per user, modify the 
 `MAX_PANELS` variable in utils.constants.py. If you want to change the minimum refresh interval, change
 `MIN_REFRESH_TIME` in utils.constants.py.