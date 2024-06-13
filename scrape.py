import json
import asyncio
from pyppeteer import launch

BASE_URL = 'http://www.ancientlocations.net/'
OUTPUT_FILE = 'places.json'

def report_schema():
    return dict.fromkeys([
        "id",
        "name",
        "other_names",
        "modern_names",
        "region",
        "section",
        "latitude",
        "longitude",
        "status",
        "info",
        "sources",
    ])
    
def save_json_file(data, filepath):
    try:
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
        print("Data successfully saved to", filepath)
    except Exception as e:
        print(f"An error occurred while saving the file: {e}")

async def get_data():
    browser = await launch(headless=True)
    page = await browser.newPage()

    places_list = []
    report_data = []

    for i in range(0, 44):  # Adjust range to 43 for main run
        await page.goto(f'{BASE_URL}Places.aspx?f={i}')
        await page.waitForSelector(f'iframe#ClientFrame')

        frame_element = await page.querySelector(f'iframe#ClientFrame')
        frame = await frame_element.contentFrame()
        hrefs = await frame.evaluate('''
            () => {
                const rows = document.querySelectorAll('table.places tr');
                return Array.from(rows, row => {
                    const onclickAttr = row.getAttribute('onclick');
                    if (onclickAttr) {
                        const match = onclickAttr.match(/href=['"](.*?)['"]/);
                        return match ? match[1] : null;
                    }
                    return null;
                }).filter(href => href !== null);
            }
        ''')
        for href in hrefs:
            places_list.append(href)
    
    print(places_list)

    for place in places_list: # remove slice when solved
        print(place)
        report = report_schema()
        place_url = f"{BASE_URL}{place}"
        print(place_url)
        await page.goto(place_url)
        
        frame_element = await page.waitForSelector(f'iframe#ClientFrame', timeout=60000)
        frame = await frame_element.contentFrame()

        try:
            table_data = await frame.evaluate('''
                () => {
                    const rows = document.querySelectorAll('table.places tr');
                    return Array.from(rows, row => {
                        const columns = row.querySelectorAll('td, th');
                        return Array.from(columns, column => column.innerText);
                    });
                }
            ''')
        except:
            print(f'no place here...........................{place}')

        report['id'] = place.split('=')[-1]
        report['name'] = table_data[0][1]

        for row in table_data:
            key = row[0].replace("(", "").replace(")", "").replace(" ", "_").lower()
            if key in report.keys():
                report[key] = row[1]
        
        report_data.append(report)
    
    await browser.close()

    save_json_file(report_data, OUTPUT_FILE)

if __name__ == "__main__":
    asyncio.run(get_data())