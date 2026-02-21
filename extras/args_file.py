import enum

# Different options on args will be used.
# Use the one you want win run_mode, below.
class run_options(enum.Enum):
	get_all_user_edits = enum.auto()
	get_titles_by_partial = enum.auto()
	get_all_in_categories = enum.auto()
	get_info_from_pages = enum.auto()
	get_pages_for_yamdwe = enum.auto()
	get_images_for_yamdwe = enum.auto()
	merge_files = enum.auto()
	subtract_files = enum.auto()
	#get_ = enum.auto()

# File for arguments with which other python files are run.
class helper_args():
	# General, understand the mediawiki API before changing
	PAUSE_BETWEEN_QUERIES: float = 0.1  #  Seconds to pause between hitting server with next query
	DEFAULT_AMOUNT_FOR_MAX_500: int = 500  # Most page results
	DEFAULT_AMOUNT_FOR_MAX_50: int = 50  # Number of pages in one query
	BASE_QUERY_REQUEST: dict[str, str] = { "action": "query", "format": "json" }
	CATEGORY_FEATURE_NAME: str = "Luokka"  # English default "Category", different in mediawiki installs in other languages
	# General for all helpers
	files_dir: str = 'test'  # All filenames below will be in this directory
	endpoint_url = 'http://xcalibur.cc.tut.fi/mediawiki/api.php'
	run_mode: run_options = run_options.get_pages_for_yamdwe
	#run_mode: run_options = run_options.subtract_files
	special_add_to_query: dict[str, str] = {} # { 'apnamespace': 102 }  # Add to special case queries
	# For getting all edits of a user
	all_edits_user: str = 'Amoeba'
	all_user_edits_savefilename: str = all_edits_user + '_edits.txt'
	# For getting all page titles with certain name parts
	wanted_parts_filename: str = 'wanted_parts.txt'
	wanted_parts_titles_savefilename: str = 'wanted_parts_titles.txt'
	# For getting all page titles within wanted categories
	categories_filename: str = 'categories.txt'  # Also used with get_pages_for_yamdwe
	in_category_titles_savefilename: str = 'categories_titles.txt'
	# For getting some properties from a list of pages
	page_props_titles_filename: str = 'save4_misc.txt'
	page_props_savefilebasename: str = 'save4_with_prop' # ".txt" will be added to end
	page_props: list[str] = ['images', 'links', 'linkshere']
	# These two are for getting the final lists of objects that
	# yamdwe would otherwise call for using allpages or allimages
	# NOTE! getting pages will also attempt to use categories_filename from above!
	#limited_pages_list_filename: str = 'save9_pages.txt'
	#limited_pages_savefilename: str = 'all_wanted_pages.json'  # This will be in json format
	limited_pages_list_filename: str = 'save7_missed_pages.txt'
	limited_pages_savefilename: str = 'missed_pages.json'  # This will be in json format
	limited_images_list_filename: str = 'save8_images.txt'
	limited_images_savefilename: str = 'all_wanted_images.json'  # This will be in json format
	# For merging titles
	merge_filenames: str = 'merge_filenames_base.txt'
	merge_titles_savefilename: str = 'merged_files.txt'
	# For subtracting titles (actually difference, these are sets)
	minuend_filename: str = 'larger.txt'  # That which is subtracted from
	subtrahend_filename: str = 'lesser.txt'  # That which is being subtracted
	subtract_result_savefilename: str = 'subtract_result.txt'

