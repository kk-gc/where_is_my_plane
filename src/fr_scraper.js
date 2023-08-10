(async () => {
    // Import the 'puppeteer' library
    const puppeteer = require('puppeteer');

    // Define the base URL for the website
    const baseUrl = 'https://www.flightradar24.com/data/';

    // Launch a new browser instance with specific options
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });

    // Create a new page within the browser
    const page = await browser.newPage();

    // Define a selector for identifying when there is no data
    const selectorWhenNoData = new String("[class^='row p-t-10 text-center']");

    // Extract command line arguments
    var arg, val;
    [arg, val] = process.argv[2].split('=');

    // Define variables for query and selector based on the argument
    switch (arg) {
        case 'flight':
            var query = new String(`flights/${val.toLowerCase()}`);
            var selector = new String("td[class^='visible-xs']");
            break;

        case 'aircraft':
            var query = new String(`aircraft/${val.toLowerCase()}`);
            var selector = new String("td[class^='visible-xs']");
            break;

        default:
            // Handle default case or provide additional code here
    }

    // Construct the full URL for the query
    let url = baseUrl + query;
    // Navigate to the constructed URL
    await page.goto(url);

    try {
        // Wait for the selector that indicates no data, with a timeout of 50 milliseconds
        await page.waitForSelector(selectorWhenNoData, { timeout: 50 })
        var reply = new Array();
        // Output the reply as JSON string and exit the process
        console.log(JSON.stringify(reply));
        process.exit();
    }
    catch {
        // If no data selector is not found, wait for the specified selector
        await page.waitForSelector(selector, { timeout: 1000 })

        // Get an array of all matched td elements
        let td_elements = await page.$$(selector);

        // Create an array to store the extracted data
        var myArr = new Array();
        // Loop through each td element and extract its inner text
        for (let index = 0; index < td_elements.length; index++) {
            let td_element = td_elements[index];
            let td_value = await page.evaluate(el => el.innerText.split('\n'), td_element);
            myArr.push(td_value);
        }
        var reply = myArr;
    }

    // Output the reply as JSON string
    console.log(JSON.stringify(reply));

    // Close the browser instance
    await browser.close();
})();


