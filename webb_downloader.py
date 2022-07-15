import os
import re
import html
import argparse
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://webbtelescope.org"
CATEGORY_URL = "https://webbtelescope.org/resource-gallery/images?itemsPerPage=15&Type=Observations&keyword=NIRCam&"

ABOUT_IMAGE_REGEX = '<h4>About This Image</h4>\s+(.+)<p><em>(NIRCam was built|MIRI was contributed).+</p>\s+<footer>'

CHUNK_SIZE = 4096

def remove_html_tags(text):
	clean = re.compile('<[^<]+?>')
	return re.sub(clean, '', text)

def parse_facts_table(soup):
	data = []

	table = soup.find('table')
	table_body = table.find('tbody')
	rows = table_body.find_all('tr')

	for row in rows:
		header = row.find('th')
		if header:
			data.append(header.text)

		cols = row.find_all('td')
		cols = [ele.text.strip() for ele in cols]
		if len(cols) == 0 or len(cols[1]) == 0: continue
		data.append([ele for ele in cols if ele]) # Get rid of empty values
	
	return data

def download_file(url, filename):
	file_extension = url.split('/')[-1].split('.')[1]
	with requests.get(url, stream=True) as r:
		r.raise_for_status()
		with open(f"{filename}.{file_extension}", 'wb') as f:
			for chunk in r.iter_content(chunk_size=CHUNK_SIZE): 
				f.write(chunk)
	return filename

def save_facts_to_file(data, filename, release_date, about_image):
	with open(f'{filename}.txt', 'w') as fp:
		fp.write(f'{release_date}\n\n')
		fp.write(f'About this image:\n{about_image}\n')

		for fact in data:
			if isinstance(fact, str):
				fp.write(f"\n{fact}\n{'-'*20}\n")
			else:
				fp.write(f"{fact[0]}: {fact[1]}\n")

def get_one_image(url):
	res = requests.get(f"{BASE_URL}{url}")

	soup = BeautifulSoup(res.text, 'html.parser')

	title_tag = soup.find("meta", property="og:title")
	about_image_match = re.search(ABOUT_IMAGE_REGEX, res.text, re.DOTALL)

	if not title_tag:
		print(f"[-] No title found: {BASE_URL}{url}")
		return

	title = html.unescape(title_tag["content"])
	filename = title.replace(' ', '_').replace('&nbsp;', '')

	if os.path.exists(f"{filename}.txt"):
		return

	print(f"[*] Downloading image: {title}")

	resource_gallery = soup.find('div', attrs={'class': 'resource-gallery-detail'})
	release_date_tag = resource_gallery.find("strong", text="Release Date:")
	
	if release_date_tag:
		release_date = release_date_tag.parent.text
	else:
		release_date = ""

	if about_image_match:
		about_image = about_image_match.group(1)
		about_image = remove_html_tags(about_image).replace('\n', '\n\n').replace('&nbsp;', '')
	else:
		about_image = ""

	links_list = resource_gallery.find("div", attrs={'class': 'media-library-links-list'}).find_all("a")
	
	for link in links_list:
		if 'Full Res' not in link.text or 'TIF' not in link.text: continue

		download_url = f"https:{link['href']}"
		download_file(download_url, filename)

	facts = parse_facts_table(soup)
	save_facts_to_file(facts, filename, release_date, about_image)

def run():
	print(f"[*] Getting observations webpage...")
	res = requests.get(CATEGORY_URL)
	print(f"[*] Got observations! Processing results.")

	soup = BeautifulSoup(res.text, 'html.parser')
	images = soup.find_all('div', attrs={'class': "ad-research-box"})

	for image in images:
		get_one_image(image.find('a')['href'])
	
	print("[*] Done.")

def main():
	parser = argparse.ArgumentParser(description="Archives James Webb Telescope's Near Infrared Camera (NIRCam) Images including metdata.")
	parser.add_argument('-o', '--output')

	args = parser.parse_args()

	if args.output is not None:
		print(f"[*] Using output folder: {args.output}")
		if not os.path.exists(args.output):
			print(f"[*] Folder does not exist. Creating it...")
			os.makedirs(args.output)

		os.chdir(args.output)
	
	run()

if __name__ == "__main__":
	main()