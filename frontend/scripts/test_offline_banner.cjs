const puppeteer = require('puppeteer-core');
const path = require('path');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.resolve(__dirname, '..', 'screenshots');

async function testOffline() {
  console.log('Testing Offline Banner via Request Interception...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  await page.setRequestInterception(true);
  page.on('request', (req) => {
    if (req.url().includes('/health') || req.url().includes('/screen')) {
      req.abort('failed');
    } else {
      req.continue();
    }
  });

  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });

  // Wait for offline banner to appear
  await page.waitForSelector('.offline-banner', { timeout: 10000 });
  const bannerText = await page.$eval('.offline-banner', (el) => el.innerText.trim());
  console.log('Detected Offline Banner:', bannerText);

  const shot = path.join(SCREENSHOT_DIR, 'backend_offline.png');
  await page.screenshot({ path: shot });
  console.log('Saved offline screenshot to:', shot);

  await browser.close();
}

testOffline().catch((err) => {
  console.error('Offline test failed:', err);
  process.exit(1);
});

