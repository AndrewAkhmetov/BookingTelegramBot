import aiosqlite
from typing import Any, Optional


class DataBase:
    # Initialize the database with the given file path
    def __init__(self, path: str) -> None:
        self.path = path

    # Create a new database
    async def create_db(self) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS info_panels_id (
                    info_panel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_id INTEGER
                )
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS index_user_id ON info_panels_id (user_id)
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS index_user_message_id ON info_panels_id (user_id, message_id)
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS info_panels (
                    info_panel_id INTEGER PRIMARY KEY,
                    last_refresh TEXT,
                    cur_position INTEGER,
                    cur_list_position INTEGER,
                    length INT,
                    FOREIGN KEY (info_panel_id) REFERENCES users_info_panels (info_panel_id) 
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS forms (
                    info_panel_id INTEGER PRIMARY KEY,
                    destination TEXT,
                    check_in TEXT,
                    check_out TEXT,
                    adults INT,
                    children INT,
                    rooms INT,
                    order_by TEXT,
                    FOREIGN KEY (info_panel_id) REFERENCES users_info_panels (info_panel_id) 
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS forms_children_age (
                    info_panel_id INTEGER,
                    age INTEGER,
                    FOREIGN KEY (info_panel_id) REFERENCES users_info_panels (info_panel_id) 
                )
            ''')
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS index_info_panel_id ON forms_children_age (info_panel_id)
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS hotels_info (
                    info_panel_id INTEGER,
                    name TEXT,
                    price INTEGER,
                    rating REAL,
                    photo TEXT,
                    link TEXT,
                    position INT,
                    PRIMARY KEY (info_panel_id, position),
                    FOREIGN KEY (info_panel_id) REFERENCES users_info_panels (info_panel_id)
                )
            ''')
            await conn.commit()

    # Insert user data into the database
    async def insert_user_data(
        self, user_id: int, message_id: int, length: int,
        last_refresh: str, hotels_info: list[dict[str, Any]],
        *form_values: tuple[str, str, str, int, int, int, str, list[Optional[int]]]
    ) -> None:
        async with aiosqlite.connect(self.path) as conn:
            # Insert user id and message id into info_panels_id table and get the generated info panel id
            async with conn.execute('''
                INSERT INTO info_panels_id (user_id, message_id) 
                VALUES (?, ?)
            ''', (user_id, message_id)) as cur:
                info_panel_id = cur.lastrowid
            # Insert the info panel data into the info_panels table
            await conn.execute('''
                INSERT INTO info_panels (
                    info_panel_id, last_refresh, cur_position, cur_list_position, length
                )
                VALUES (?, ?, ?, ?, ?)
            ''', (info_panel_id, last_refresh, 1, 1, length))

            # Unpack form values
            destination, check_in, check_out, adults, children, rooms, order_by, children_age = form_values
            await conn.execute('''
                INSERT INTO forms (
                    info_panel_id, destination, check_in, check_out, adults, children, rooms, order_by
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (info_panel_id, destination, check_in, check_out, adults, children, rooms, order_by))

            # Insert each child's age into the forms_children_age table
            for age in children_age:
                await conn.execute('''
                    INSERT INTO forms_children_age (info_panel_id, age)
                    VALUES (?, ?)
                ''', (info_panel_id, age))

            # Insert hotel information into the hotels_info table with the corresponding position
            for position, hotel_info in enumerate(hotels_info, start=1):
                await conn.execute('''
                    INSERT INTO hotels_info (
                        info_panel_id, name, price, rating, photo, link, position
                    ) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        info_panel_id,
                        hotel_info.get('Name'),
                        hotel_info.get('Price'),
                        hotel_info.get('Rating'),
                        hotel_info.get('Photo'),
                        hotel_info.get('Link'),
                        position
                    )
                )

            await conn.commit()

    # Get an info panel based on user_id and message_id
    async def get_info_panel(self, user_id: int, message_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute('''
                SELECT * FROM info_panels
                WHERE info_panel_id = (
                    SELECT info_panel_id FROM info_panels_id
                    WHERE user_id = ? AND message_id = ?
                )
            ''', (user_id, message_id)) as cur:
                info_panel = await cur.fetchone()

        # Return None if no info panel is found, otherwise return the info panel data
        if not info_panel:
            return None
        return {
            'info_panel_id': info_panel[0],
            'last_refresh': info_panel[1],
            'cur_position': info_panel[2],
            'cur_list_position': info_panel[3],
            'length': info_panel[4]
        }

    # Update the current position of an info panel and get the corresponding hotel info
    async def update_position_get_hotel(self, info_panel_id: int, cur_position: int) -> dict[str, Any]:
        async with aiosqlite.connect(self.path) as conn:
            # Update the current position in the info_panels table
            await conn.execute('''
                UPDATE info_panels
                SET cur_position = ?
                WHERE info_panel_id = ?
            ''', (cur_position, info_panel_id))
            await conn.commit()

            # Select the hotel information based on the updated position
            async with conn.execute('''
                SELECT name, price, rating, photo, link, destination, check_in, check_out
                FROM hotels_info
                JOIN forms ON hotels_info.info_panel_id = forms.info_panel_id
                WHERE hotels_info.info_panel_id = ? and position = ?
            ''', (info_panel_id, cur_position)) as cur:
                hotel_info = await cur.fetchone()

        # Return the hotel information as a dictionary
        return {
            'name': hotel_info[0],
            'price': hotel_info[1],
            'rating': hotel_info[2],
            'photo': hotel_info[3],
            'link': hotel_info[4],
            'destination': hotel_info[5],
            'check_in': hotel_info[6],
            'check_out': hotel_info[7]
        }

    # Update the list position and get the corresponding list of hotels
    async def update_list_position_get_hotels(self, info_panel_id: int, cur_list_position: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as conn:
            # Update the current list position in the info_panels table
            await conn.execute('''
                UPDATE info_panels
                SET cur_list_position = ?
                WHERE info_panel_id = ?
            ''', (cur_list_position, info_panel_id))
            await conn.commit()

            # Select a list of hotels based on the updated list position
            async with conn.execute('''
                SELECT name, price, rating
                FROM hotels_info
                WHERE info_panel_id = ?
                AND position >= ?
                AND position < ?
            ''', (info_panel_id, cur_list_position, cur_list_position + 5)) as cur:
                hotels_info = await cur.fetchall()

        # Return the list of hotels as a list of dictionaries
        return [
            {
                'name': hotel_info[0],
                'price': hotel_info[1],
                'rating': hotel_info[2]
            } for hotel_info in hotels_info
        ]

    # Update the hotels_info table with new data and refresh the info panel
    async def update_hotels_info_panel(
            self, info_panel_id: int, hotels_info: list[dict], hotels_info_length: int, last_refresh: str
    ) -> None:
        async with aiosqlite.connect(self.path) as conn:
            # Delete existing hotel information for the given info_panel_id
            await conn.execute('''
                DELETE FROM hotels_info
                WHERE info_panel_id = ?
            ''', (info_panel_id,))

            # Insert new hotel information into the hotels_info table
            for position, hotel_info in enumerate(hotels_info, start=1):
                await conn.execute('''
                    INSERT INTO hotels_info (
                        info_panel_id, name, price, rating, photo, link, position
                    ) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        info_panel_id, hotel_info.get('Name'), hotel_info.get('Price'),
                        hotel_info.get('Rating'), hotel_info.get('Photo'), hotel_info.get('Link'),
                        position
                    )
                )

            # Update the last refresh time and reset the current positions in the info_panels table
            await conn.execute('''
                UPDATE info_panels
                SET last_refresh = ?, cur_position = ?, cur_list_position = ?, length = ?
                WHERE info_panel_id = ?
            ''', (last_refresh, 1, 1, hotels_info_length, info_panel_id))

            await conn.commit()

    # Get form and info panel information for a specific info panel based on user_id and message_id
    async def get_form_info_panel(self, user_id: int, message_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select the info panel id, message id and last refresh time from the info_panels_id table
            async with conn.execute('''
                SELECT info_panels_id.info_panel_id, message_id, last_refresh FROM info_panels_id
                JOIN info_panels ON info_panels_id.info_panel_id = info_panels.info_panel_id
                WHERE user_id = ? AND message_id = ?
            ''', (user_id, message_id)) as cur:
                info_panel = await cur.fetchone()

            # Return None if no info panel is found
            if not info_panel:
                return
            # Get info panel id
            info_panel_id = info_panel[0]

            # Get the form data from the forms table
            async with conn.execute('''
                SELECT * FROM forms
                WHERE info_panel_id = ? 
            ''', (info_panel_id,)) as cur:
                form = await cur.fetchone()

            # Get the children's ages from the forms_children_age table
            async with conn.execute('''
                SELECT age FROM forms_children_age
                WHERE info_panel_id = ?
            ''', (info_panel_id,)) as cur:
                form_children_age = await cur.fetchall()

            # Return the collected information as a dictionary
            return {
                'info_panel_id': info_panel[0],
                'message_id': info_panel[1],
                'last_refresh': info_panel[2],
                'destination': form[1],
                'check_in': form[2],
                'check_out': form[3],
                'adults': form[4],
                'children': form[5],
                'rooms': form[6],
                'order_by': form[7],
                'children_age': [age[0] for age in form_children_age] if form_children_age else []
            }

    # Get all forms and info panels information for a specific info panel based on user_id
    async def get_all_forms_info_panels(self, user_id: int) -> Optional[list[dict[str, Any]]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select the info panels ids, messages ids and last refresh times from the info_panels_id table
            async with conn.execute('''
                SELECT info_panels_id.info_panel_id, message_id, last_refresh FROM info_panels_id
                JOIN info_panels ON info_panels_id.info_panel_id = info_panels.info_panel_id
                WHERE user_id = ?  
            ''', (user_id,)) as cur:
                info_panels = await cur.fetchall()

            # Return None if no info panels are found
            if not info_panels:
                return

            # Get the forms data from the forms table
            async with conn.execute('''
                SELECT * FROM forms
                WHERE info_panel_id IN (
                    SELECT info_panel_id FROM info_panels_id
                    WHERE user_id = ?
                )
            ''', (user_id,)) as cur:
                forms = await cur.fetchall()

            # Get the children's ages from the forms_children_age table
            forms_children_age = []
            for info_panel in info_panels:
                info_panel_id = info_panel[0]
                async with conn.execute('''
                    SELECT age FROM forms_children_age
                    WHERE info_panel_id = ?
                ''', (info_panel_id,)) as cur:
                    form_children_age = await cur.fetchall()
                forms_children_age.append([age[0] for age in form_children_age] if form_children_age else [])

        # Return a list of dictionaries containing all collected information
        return [
            {
                'info_panel_id': info_panel[0],
                'message_id': info_panel[1],
                'last_refresh': info_panel[2],
                'destination': form[1],
                'check_in': form[2],
                'check_out': form[3],
                'adults': form[4],
                'children': form[5],
                'rooms': form[6],
                'order_by': form[7],
                'children_age': form_children_age
            } for info_panel, form, form_children_age in zip(info_panels, forms, forms_children_age)
        ]

    # Delete an info panel and all related data from the database
    async def delete_info_panel(self, info_panel_id: int) -> None:
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute('''
                DELETE FROM info_panels_id
                WHERE info_panel_id = ?
            ''', (info_panel_id,))
            await conn.execute('''
                DELETE FROM info_panels
                WHERE info_panel_id = ?
            ''', (info_panel_id,))
            await conn.execute('''
                DELETE FROM forms
                WHERE info_panel_id = ?
            ''', (info_panel_id,))
            await conn.execute('''
                DELETE FROM forms_children_age
                WHERE info_panel_id = ?
            ''', (info_panel_id,))
            await conn.execute('''
                DELETE FROM hotels_info
                WHERE info_panel_id = ?
            ''', (info_panel_id,))
            await conn.commit()

    # Get all info panels for a specific user
    async def get_all_info_panels(self, user_id: int) -> Optional[list[dict[str, int]]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select all info panels ids and messages ids for the given user id
            async with conn.execute('''
                SELECT info_panel_id, message_id FROM info_panels_id
                WHERE user_id = ?
            ''', (user_id,)) as cur:
                info_panels = await cur.fetchall()

        # Return None if no info panels are found,
        # otherwise return a list of dictionaries containing the info panels ids and messages ids
        if not info_panels:
            return
        return [
            {
                'info_panel_id': info_panel[0],
                'message_id': info_panel[1]
            } for info_panel in info_panels
        ]

    # Count the number of info panels associated with a given user id and return it
    async def count_all_info_panels(self, user_id: int) -> Optional[int]:
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute('''
                SELECT COUNT(info_panel_id) FROM info_panels_id
                WHERE user_id = ?
            ''', (user_id,)) as cur:
                info_panel_count = await cur.fetchone()
        return info_panel_count[0]

    # Get user details from the forms table based on the user_id
    async def get_user_details(self, user_id: int) -> Optional[list[dict[str, Any]]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select the form details for all info panels for the user
            async with conn.execute('''
                SELECT info_panel_id, adults, children, rooms, order_by FROM forms
                WHERE info_panel_id IN (
                    SELECT info_panel_id FROM info_panels_id
                    WHERE user_id = ?
                )
            ''', (user_id,)) as cur:
                user_details = await cur.fetchall()

            # Return the user details as a dictionary or None if no details are found
            if not user_details:
                return None

            # Select the ages of children for all info panels for the user
            user_details_children_age = []
            for user_detail in user_details:
                info_panel_id = user_detail[0]
                async with conn.execute('''
                    SELECT age FROM forms_children_age
                    WHERE info_panel_id = ? 
                ''', (info_panel_id,)) as cur:
                    children_age = await cur.fetchall()
                user_details_children_age.append([age[0] for age in children_age] if children_age else [])

        return [
            {
                'adults': user_detail[1],
                'children': user_detail[2],
                'rooms': user_detail[3],
                'order_by': user_detail[4],
                'children_age': children_age
            } for user_detail, children_age in zip(user_details, user_details_children_age)
        ]

    # Get a list of hotels sorted by rating and price for a given user_id
    async def get_hotels_info_rating(self, user_id: int) -> Optional[list[dict[str, Any]]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select hotel and form details sorted by rating, price from joined hotels_info and forms table
            async with conn.execute('''
               SELECT name, price, rating, destination, check_in, check_out, photo, link
               FROM hotels_info
               JOIN forms ON hotels_info.info_panel_id = forms.info_panel_id
               WHERE hotels_info.info_panel_id IN (
                   SELECT info_panels_id.info_panel_id FROM info_panels_id
                   WHERE user_id = ? 
               )
                ORDER BY rating DESC, price
            ''', (user_id, )) as cur:
                hotels_info = await cur.fetchall()

        # Return the list of hotels or None if no hotels are found
        if not hotels_info:
            return
        return [
            {
                'Name': hotel_info[0],
                'Price ($)': hotel_info[1],
                'Rating': hotel_info[2],
                'Destination': hotel_info[3],
                'Check-in': hotel_info[4],
                'Check-out': hotel_info[5],
                'Photo': hotel_info[6],
                'Link': hotel_info[7]
            } for hotel_info in hotels_info
        ]

    # Get a list of hotels sorted by price and rating for a given user_id
    async def get_hotels_info_price(self, user_id: int) -> Optional[list[dict[str, Any]]]:
        async with aiosqlite.connect(self.path) as conn:
            # Select hotel and form details sorted by price, rating from joined hotels_info and forms table
            async with conn.execute('''
                   SELECT name, price, rating, destination, check_in, check_out, photo, link
                   FROM hotels_info
                   JOIN forms ON hotels_info.info_panel_id = forms.info_panel_id
                   WHERE hotels_info.info_panel_id IN (
                       SELECT info_panels_id.info_panel_id FROM info_panels_id
                       WHERE user_id = ? 
                   )
                   ORDER BY price, rating DESC
               ''', (user_id,)) as cur:
                hotels_info = await cur.fetchall()

        # Return the list of hotels or None if no hotels are found
        if not hotels_info:
            return
        return [
            {
                'Name': hotel_info[0],
                'Price ($)': hotel_info[1],
                'Rating': hotel_info[2],
                'Destination': hotel_info[3],
                'Check-in': hotel_info[4],
                'Check-out': hotel_info[5],
                'Photo': hotel_info[6],
                'Link': hotel_info[7]
            } for hotel_info in hotels_info
        ]
