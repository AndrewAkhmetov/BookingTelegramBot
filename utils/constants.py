# Maximum number of workers for ThreadPoolExecutor
MAX_WORKERS = 8

# Constant for the minimum refresh interval in seconds
MIN_REFRESH_TIME = 30

# Constant for the maximum amount of information panel by user
MAX_PANELS = 6

# How many times parser will click on 'Load More' button in Booking.com
LOAD_MORE_BUTTON_CLICKS = 2

# Dictionary mapping sorting options to their descriptions from Booking.com
SORT_OPTIONS_DESCRIPTIONS = {
    'popularity': 'Top picks for long stays',
    'upsort_bh': 'Homes & apartments first',
    'price': 'Price (lowest first)',
    'review_score_and_price': 'Best reviewed & lowest price',
    'class': 'Property rating (high to low)',
    'class_asc': 'Property rating (low to high)',
    'class_and_price': 'Property rating and price',
    'distance_from_search': 'Distance From Downtown',
    'bayesian_review_score': 'Top Reviewed'
}
