# Partial MediaWiki to DokuWiki conversion
import os.path
import re
import json

# All the arguments for running pmw2dy
class pmw2dw_args():
	#   Change these as necessary
	# File containg one json object to use as replacements, key being old, value being new
	template_replacements_filename: str = os.path.join('extras', 'test', 'template_conversion.json')
	# Keep mediawiki tables, if using a plugin in dokuwiki such as exttab3
	keep_tables: bool = True
	# What replacements will be made within the table string, since they won't be handled by the parser.
	in_table_style_replacements: list[tuple[str, str]] = [("'''", "**"), ("''", "//")]  # '''
	# Other replacements to make within the mediawiki content
	other_html_replacements: list[tuple[str, str]] = [("<BR>", r"\\ "), ("<BR/>", r"\\ "), ("<BR />", r"\\ "), ("<U>", "__"), ("</U>", "__")]
	# What internal link types need to be renamed
	link_mappings: dict[str, str] = { "Kuva": "Image", "Tiedosto": "File", "Luokka": "Category" }
	#   These are probably fine as is
	# Special markers to denote where the mediawiki table strings go
	tables_start_marker: str = '<__pmw2dw_table>'
	tables_end_marker: str = '</__pmw2dw_table>'

# Main class to actually do all the substitutions & stuff
class pmw2dw_converter():
	def __init__(self, args: pmw2dw_args):
		# For replacing template contents
		self.template_replacements: dict[str, str] | None = None
		if args.template_replacements_filename:
			with open(args.template_replacements_filename, mode='r', encoding="utf-8") as f:
				self.template_replacements = json.load(f)
		# For keeping mediawiki-formtted tables
		self.table_contents: list[str] | None = None
		# For fixing ArticleLinks into ImageLinks or CategoryLinks
		self.link_maps: list[tuple[re.Pattern, str]] = []
		for in_txt, out_txt in args.link_mappings.items():
			regex_pattern: re.Pattern = re.compile(r"\[\[" + in_txt + r":(.+)\]\]")
			replacement: str = "[[" + out_txt + ":" + r"\1" + "]]"
			self.link_maps.append( (regex_pattern, replacement) )
		# For use of our methods
		self.case_id: str = ""
		self.args: pmw2dw_args = args

	# Separate tables from mediawiki string
	def separate_tables(self, content: str) -> str:
		if not self.args.keep_tables:
			return content
		slice_locs = find_nested_blocks('{|', '|}', content, self.case_id)
		not_tables: list[str] = []
		self.table_contents = []
		prev_end: int = 0
		for counter, splits in enumerate(slice_locs):
			start: int = splits[0]
			end: int = splits[1]
			not_tables.append(content[prev_end:start])
			not_tables.append(self.args.tables_start_marker + str(counter) + self.args.tables_end_marker)
			prev_end = end
			table: str = content[start:end]
			for repl in self.args.in_table_style_replacements:
				pattern = repl[0] + '(.+)' + repl[0]
				replacement = repl[1] + r'\1' + repl[1]
				table = re.sub(pattern, replacement, table)
			# Tables may also contain templates
			table = self.replace_templates(table)
			self.table_contents.append(table)
		not_tables.append(content[prev_end:])
		return "".join(not_tables)

	# Join mediawiki tables back in to dokuwiki string
	def join_tables_back_in(self, content: str) -> str:
		if not self.args.keep_tables:
			return content
		regex = self.args.tables_start_marker + '([0-9]+)' + self.args.tables_end_marker
		def get_table(matchobj):
			return self.table_contents[int(matchobj.group(1))]
		return re.sub(regex, get_table, content)

	# Replacing locally translated link types to en versions
	def replace_links(self, content: str) -> str:
		for regex_pattern, replacement in self.link_maps:
			content = regex_pattern.sub(replacement, content)
		return content

	# Replace templates with what should be acceptable dokuwiki files
	def replace_templates(self, content: str) -> str:
		if '{{' not in content or not self.template_replacements:
			return content
		for old_templ, new_file in self.template_replacements.items():
			content = content.replace(old_templ, new_file)
		return content

	# Replace any other html stuff
	def replace_other_html(self, content: str) -> str:
		for old_templ, new_file in self.args.other_html_replacements:
			content = content.replace(old_templ, new_file)
		return content

	# The order here matters, as separating tables removes them from
	# the string that will be parsed and converted to dokuwiki markup
	def pre_process(self, content: str, identifier: str) -> str:
		self.case_id = identifier
		content = self.separate_tables(content)
		content = self.replace_templates(content)
		content = self.replace_links(content)
		return content

	def post_process(self, content: str) -> str:
		content = self.join_tables_back_in(content)
		content = self.replace_other_html(content)
		self.case_id = ""
		return content


# A function to find top-level blocks from text,
# with possible inner nested blocks left within the top-level ones.
def find_nested_blocks(start: str, end: str, text: str, identifier: str) -> list[int]:
	if start == end:
		# Could raise some Exception at these, being lazy for now.
		print(f"Block start and end cannot be same! ({identifier})")
		return []
	
	# Function for finding all locations of substrings.
	# Does not find overlapping strings.
	def find_all(pattern: str):
		ind: int = text.find(pattern)
		while ind != -1:
			yield ind
			ind = text.find(pattern, ind+len(pattern))
	
	starts: list[int] = list(find_all(start))
	ends: list[int] = list(find_all(end))
	if len(starts) != len(ends):
		print(f"Mismatch in block start and end amount! ({identifier})")
		return []
	elif not starts:
		return []
	lengths: int = len(starts)
	#print(f"DEBUG, lengths: {lengths}, starts: {starts}, ends: {ends}")
	results: list[int] = []
	s: int = 0
	e: int = 0
	depth_count: int = 0
	outermost_start: int | None = None
	while True:
		start_loc: int = starts[s] if s < lengths else len(text)+1
		end_loc: int = ends[e] if e < lengths else len(text)+1
		#print(f"DEBUG, s[{s}]tart_loc: {start_loc}, e[{e}]nd_loc: {end_loc}, depth: {depth_count}")
		if start_loc < end_loc:
			if depth_count == 0:
				outermost_start = start_loc
			depth_count += 1
			s += 1
		elif start_loc > end_loc:
			depth_count -= 1
			if depth_count < 0:
				print(f"Block closed without one being open, Error! ({identifier})")
				return []
			elif depth_count == 0:
				results.append( (outermost_start, end_loc + len(end)) )
				outermost_start = None
			else:
				pass  # Decreasing depth, everything Ok.
			e += 1
		else:  # Should never happen
			print(f"Start and end of block at same location, Error! ({identifier})")
			return None
		if s >= lengths and e >= lengths:
			break
	return results

