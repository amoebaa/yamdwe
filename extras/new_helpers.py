#!/usr/bin/python3
import sys
import time
import os.path
import collections
import requests
import json
from args_file import run_options, helper_args

parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_directory)
from pmw2dw import find_nested_blocks

"""
Based on:
https://www.mediawiki.org/wiki/Special:MyLanguage/API:Usercontribs#Python
"""
def request_with_continue(request: dict[str, str], args: helper_args):
	prev_continue: dict = {}
	counter: int = 0
	while True:
		counter += 1
		print(f"This is request {args.mode_name}/{counter}")
		# Don't modify original request, just in case...
		req: dict[str, str] = request.copy()
		req.update(args.special_add_to_query)
		# but add possible continue values from previous request
		req.update(prev_continue)
		# Call API
		full_result = requests.get(args.endpoint_url, params=req)
		json_result = full_result.json()
		if 'error' in json_result:
			raise Exception(json_result['error'])
		if 'warnings' in json_result:
			print(json_result['warnings'])
		if 'query' in json_result:
			yield json_result['query']
		if 'continue' not in json_result:
			break
		prev_continue = json_result['continue']
		if args.PAUSE_BETWEEN_QUERIES:
			time.sleep(args.PAUSE_BETWEEN_QUERIES)

def save_to_file(content: str|list[str], filename: str, args: helper_args):
	filepath = os.path.join(args.files_dir, filename)
	if isinstance(content, str):
		with open(filepath, mode='w', encoding="utf-8") as f:
			f.write(content)
	elif isinstance(content, list):
		with open(filepath, mode='w', encoding="utf-8") as f:
			f.write("\n".join(content))
	else:
		print(f"Wanted to save to {filename} but given content neither str or list!")

def read_clean_list(filename: str, args: helper_args) -> list[str]:
	filepath = os.path.join(args.files_dir, filename)
	result_list: list[str] = []
	with open(filepath, mode='r', encoding="utf-8") as f:
		for possible_line in f:
			if possible_line.strip():
				result_list.append(possible_line.strip())
	return result_list

# Gets everything a specific user has done to the wiki
def get_user_edits(args: helper_args):
	user_edits_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	specific_query_additions: dict[str, str] = { 'list': 'usercontribs', 'ucuser': args.all_edits_user, 'uclimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	user_edits_query.update(specific_query_additions)
	modified_pages: set[str] = set()
	for result in request_with_continue(user_edits_query, args):
		for item in result['usercontribs']:
			modified_pages.add(item['title'])
	save_to_file(sorted(modified_pages), args.all_user_edits_savefilename, args)

# Get every page on the wiki where the page name contains a wanted part
def get_pages_by_partial_names(args: helper_args):
	wanted_parts: list[str] = read_clean_list(args.wanted_parts_filename, args)
	pages_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	specific_query_additions: dict[str, str] = { 'list': 'allpages', 'aplimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	pages_query.update(specific_query_additions)
	titles_result: list[str] = []
	for result in request_with_continue(pages_query, args):
		for item in result['allpages']:
			for part in wanted_parts:
				if part in item['title']:
					titles_result.append(item['title'])
					break
	save_to_file(titles_result, args.wanted_parts_titles_savefilename, args)

# Get every page from all categories in list
def get_all_from_categories(args: helper_args):
	pages_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	category_names: list[str] = read_clean_list(args.categories_filename, args)
	query_additions: dict[str, str] = { 'list': 'categorymembers', 'cmtype': 'page', 'cmlimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	pages_query.update(query_additions)
	output: list[str] = []
	orig_mode: str = args.mode_name
	for category_name in category_names:
		pages_query['cmtitle'] = args.CATEGORY_FEATURE_NAME + ':' + category_name
		args.mode_name = orig_mode + ':' + category_name
		for result in request_with_continue(pages_query, args):
			for item in result['categorymembers']:
				output.append(item['title'])
	args.mode_name = orig_mode
	save_to_file(output, args.in_category_titles_savefilename, args)

# Getting wanted properties from a bunch of pages
def get_page_props_for_many_pages(args: helper_args):
	pages_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	page_titles: list[str] = read_clean_list(args.page_props_titles_filename, args)
	#query_additions: dict[str, str] = { 'prop': '|'.join(args.page_props.keys()) }
	query_additions: dict[str, str] = { 'prop': '|'.join(args.page_props) }
	#'categorymembers', 'cmtype': 'page', 'cmlimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	pages_query.update(query_additions)
	output: dict[str, set] = collections.defaultdict(set)
	orig_mode: str = args.mode_name
	# With 3.12, could use  itertools.batched(page_titles, args.DEFAULT_AMOUNT_FOR_MAX_50)
	batched_titles: list[list[str]] = []  # page_titles[i:i+args.DEFAULT_AMOUNT_FOR_MAX_50] for i in range(0, len(page_titles), args.DEFAULT_AMOUNT_FOR_MAX_50) ]
	for i in range(0, len(page_titles), args.DEFAULT_AMOUNT_FOR_MAX_50):
		batched_titles.append(page_titles[i:i+args.DEFAULT_AMOUNT_FOR_MAX_50])
	for batch in batched_titles:
		pages_query['titles'] = '|'.join(batch)
		args.mode_name = orig_mode + '/' + batch[0] + '-' + batch[-1]
		for result in request_with_continue(pages_query, args):
			for page in result['pages']:
				for prop in args.page_props:
					if prop in result['pages'][page]:
						prop_list = result['pages'][page][prop]
						for item in prop_list:
							output[prop].add(item['title'])
	args.mode_name = orig_mode
	for prop in output:
		save_to_file(sorted(output[prop]), args.page_props_savefilebasename + '_' + prop + '.txt', args)

# Simple recursive function to get data from deep within a object hierarchy
def get_from_deep_path(obj: list|dict, path: list):
	if len(path) == 1:
		if isinstance(obj, dict) and path[0] in obj:
			return obj[path[0]]
		elif isinstance(obj, list) and isinstance(path[0], int) and path[0] < len(obj):
			return obj[path[0]]
		else:
			print(f"Last of path missing, returning None!")
			return None
	elif isinstance(obj, dict) and path[0] in obj:
		return get_from_deep_path(obj[path[0]], path[1:])
	elif isinstance(obj, list) and isinstance(path[0], int) and path[0] < len(obj):
		return get_from_deep_path(obj[path[0]], path[1:])
	else:
		print(f"Unable to pursue deep path, had {len(path)} levels remaining: {path}")
		return None

# Getting html comments from a bunch of pages, copied from page_props
def get_comments_for_many_pages(args: helper_args):
	pages_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	page_titles: list[str] = read_clean_list(args.comments_titles_filename, args)
	query_additions: dict[str, str] = { 'prop': 'revisions', 'rvprop': 'content', 'rvslots': '*' }
	pages_query.update(query_additions)
	output: dict[str, dict] = {} # collections.defaultdict(dict)

	# Search for comments, add to output (with location) if there are any
	def add_comment_parts(wikitext: str, title: str):
		comment_positions: list[int] = find_nested_blocks('<!--', '-->', wikitext, title)
		if not comment_positions:
			return
		page_data: list[dict[str, str]] = []
		for counter, splits in enumerate(comment_positions):
			start: int = splits[0]
			end: int = splits[1]
			page_data.append({ "start": str(start), "end": str(end), "text": wikitext[start:end] })
		output[title] = page_data

	orig_mode: str = args.mode_name
	batched_titles: list[list[str]] = []
	for i in range(0, len(page_titles), args.DEFAULT_AMOUNT_FOR_MAX_50):
		batched_titles.append(page_titles[i:i+args.DEFAULT_AMOUNT_FOR_MAX_50])
	for batch in batched_titles:
		pages_query['titles'] = '|'.join(batch)
		args.mode_name = orig_mode + '/' + batch[0] + '-' + batch[-1]
		for result in request_with_continue(pages_query, args):
			for page in result['pages']:
				page_data: dict = result['pages'][page]
				#wikitext: str = page_data['revisions'][0]['slots']['main']['*']
				wikitext: str = get_from_deep_path(page_data, ['revisions', 0, 'slots', 'main', '*'])
				if not wikitext:
					print(f"Page {page_data['title']} had no content!")
					continue
				add_comment_parts(wikitext, page_data['title'])
	args.mode_name = orig_mode
	print(f"Given titles: {len(page_titles)}, got items with comments {len(output)}")
	save_to_file(json.dumps(output, indent='\t'), args.comments_savefilename, args)


# A general function to get actual json result items, filtered by title
def get_object_if_title_on_list(wanted_titles: list[str], query_additions: dict[str, str], args: helper_args):
	pages_query: dict[str, str] = args.BASE_QUERY_REQUEST.copy()
	pages_query.update(query_additions)
	wanted_items: list[dict[str, str]] = []
	for result in request_with_continue(pages_query, args):
		for item in result[query_additions['list']]:
			if item['title'] in wanted_titles:
				wanted_items.append(item)
			if ' ' in item['title']: 
				if item['title'].replace(' ', '_') in wanted_titles:
					wanted_items.append(item)
	return wanted_items

# Get json data on pages, ready for yamdwe to use.  Also goes through categories.
def create_partial_pages_list_for_yamdwe(args: helper_args):
	wanted_titles: list[str] = read_clean_list(args.limited_pages_list_filename, args)
	query_additions: dict[str, str] = { 'list' : 'allpages', 'aplimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	wanted_items: list = get_object_if_title_on_list(wanted_titles, query_additions, args)
	if (args.categories_filename):
		category_names: list[str] = read_clean_list(args.categories_filename, args)
		print(f"Found {len(category_names)} categories to also check for page data.")
		query_additions: dict[str, str] = { 'list': 'categorymembers', 'cmtype': 'page', 'cmlimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
		orig_mode: str = args.mode_name
		for category_name in category_names:
			query_additions['cmtitle'] = args.CATEGORY_FEATURE_NAME + ':' + category_name
			args.mode_name = orig_mode + ':' + category_name
			wanted_items.extend(get_object_if_title_on_list(wanted_titles, query_additions, args))
		args.mode_name = orig_mode
	# Make sure we get unique ones
	unique_wanted_items = list( { item['pageid']: item for item in wanted_items }.values() )
	wanted_items = sorted(unique_wanted_items, key=lambda item: item['title'])
	title_counts: collections.Counter = collections.Counter([ i['title'] for i in wanted_items ])
	multiples: list[str] = []
	for title, amount in title_counts.most_common():
		if amount < 2:
			break
		multiples.append(f"{title} : {amount}")
	if multiples:
		print("Found multiples of following titles:\n" + ", ".join(multiples))
	print(f"Wanted titles: {len(wanted_titles)}, got items {len(wanted_items)}")
	save_to_file(json.dumps(wanted_items, indent='\t'), args.limited_pages_savefilename, args)

# Get json data on images, ready for yamdwe to use.
def create_partial_images_list_for_yamdwe(args: helper_args):
	wanted_titles: list[str] = read_clean_list(args.limited_images_list_filename, args)
	query_additions: dict[str, str] = { 'list' : 'allimages', 'ailimit': args.DEFAULT_AMOUNT_FOR_MAX_500 }
	wanted_items: list = get_object_if_title_on_list(wanted_titles, query_additions, args)
	print(f"Wanted titles: {len(wanted_titles)}, got items {len(wanted_items)}")
	save_to_file(json.dumps(wanted_items, indent='\t'), args.limited_images_savefilename, args)


# Read a list of files, read titles from all files, write unique titles into single file
def merge_titles(args: helper_args):
	go_through_files: list[str] = read_clean_list(args.merge_filenames, args)
	all_titles: list[str] = []
	for filename in go_through_files:
		all_titles.extend(read_clean_list(filename, args))
	save_to_file(sorted(set(all_titles)), args.merge_titles_savefilename, args)

# Read a list of files, read titles from all files, write unique titles into single file
def subtract_titles(args: helper_args):
	minuend: set[str] = set(read_clean_list(args.minuend_filename, args))
	subtrahend: set[str] = set(read_clean_list(args.subtrahend_filename, args))
	save_to_file(sorted(minuend - subtrahend), args.subtract_result_savefilename, args)


def test_stuff():
	ENDPOINT_URL = 'http://xcalibur.cc.tut.fi/mediawiki/api.php'
	sess = requests.Session()
	#PARAMS = { "action": "query", "format": "json", "titles": "KoExalted:Paikat_v1", "prop": "images|links|linkshere" }
	#PARAMS = { "action": "query", 'list' : 'allpages', "format": "json"}
	#PARAMS = { "action": "query", 'pageids' : '1536|1546', 'prop': 'info|pageprops', "format": "json"}
	PARAMS = { "action": "query", 'titles' : 'Foo|‎Bar', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': '*', "format": "json"}
	resp = sess.get(url=ENDPOINT_URL, params=PARAMS)
	DATA = resp.json()
	#query_resp = DATA["query"]
	#print(query_resp)
	print(DATA)

if __name__ == "__main__":
	#test_stuff()
	#sys.exit()
	args = helper_args
	args.mode_name: str = args.run_mode.name
	print(f"Running helper in mode {args.mode_name}")
	match args.run_mode:
		case run_options.get_all_user_edits:
			get_user_edits(args)
		case run_options.get_titles_by_partial:
			get_pages_by_partial_names(args)
		case run_options.get_all_in_categories:
			get_all_from_categories(args)
		case run_options.get_info_from_pages:
			get_page_props_for_many_pages(args)
		case run_options.get_comments_from_pages:
			get_comments_for_many_pages(args)
		case run_options.get_pages_for_yamdwe:
			create_partial_pages_list_for_yamdwe(args)
		case run_options.get_images_for_yamdwe:
			create_partial_images_list_for_yamdwe(args)
		case run_options.merge_files:
			merge_titles(args)
		case run_options.subtract_files:
			subtract_titles(args)

