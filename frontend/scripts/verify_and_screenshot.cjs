const puppeteer = require('puppeteer-core');
const path = require('path');
const fs = require('fs');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_URL = 'http://127.0.0.1:8000';
const SCREENSHOT_DIR = path.resolve(__dirname, '..', 'screenshots');

const FIXTURES = {
  likelyGenuine: 'D:\\pharmavaluate\\data\\processed\\pill\\jpg\\000009.jpg',
  inconclusive: 'D:\\pharmavaluate\\data\\processed\\pill\\jpg\\000004.jpg',
  unknownProduct: 'D:\\pharmavaluate\\data\\processed\\pill\\jpg\\000010.jpg',
  retakeBlank: path.resolve(__dirname, '..', 'test_fixtures', 'retake_blank.jpg'),
  notAnImage: path.resolve(__dirname, '..', 'test_fixtures', 'not_an_image.txt'),
  over10Mb: path.resolve(__dirname, '..', 'test_fixtures', 'over_10mb.jpg'),
};

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function run() {
  console.log('====================================================');
  console.log('PharmaValuate Frontend E2E Verification & Screenshots');
  console.log('Notice: screening aid, verify manually');
  console.log('====================================================');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  try {
    // 1. Load FastAPI frontend
    console.log(`\n[1/8] Opening ${BASE_URL}...`);
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    const pageTitle = await page.title();
    console.log(`Page Title: "${pageTitle}"`);

    // Verify persistent disclaimer banner is present
    const bannerText = await page.$eval('.top-disclaimer-banner', el => el.innerText.trim());
    console.log(`Persistent Top Banner: "${bannerText}"`);

    // 2. Test Image 1: Likely Genuine
    console.log('\n[2/8] Screening Image 1: Likely Genuine (000009.jpg)...');
    const input1 = await page.$('#pill-file-input');
    await input1.uploadFile(FIXTURES.likelyGenuine);
    await new Promise(r => setTimeout(r, 600));

    await page.click('button.btn-primary');
    await page.waitForSelector('.result-card:not([aria-busy="true"]) .label-badge', { timeout: 30000 });

    const badge1 = await page.$eval('.label-badge', el => el.innerText.trim());
    console.log(`Result badge: "${badge1}"`);
    if (!badge1.includes('Likely Genuine')) throw new Error(`Expected Likely Genuine, got: ${badge1}`);

    const shot1 = path.join(SCREENSHOT_DIR, 'likely_genuine.png');
    await page.screenshot({ path: shot1, fullPage: true });
    console.log(`Saved screenshot: ${shot1}`);

    // 3. Test Image 2: Inconclusive
    console.log('\n[3/8] Screening Image 2: Inconclusive (000004.jpg)...');
    await page.click('button.btn-secondary'); // Clear
    await new Promise(r => setTimeout(r, 400));

    const input2 = await page.$('#pill-file-input');
    await input2.uploadFile(FIXTURES.inconclusive);
    await new Promise(r => setTimeout(r, 600));

    await page.click('button.btn-primary');
    await page.waitForFunction(
      () => {
        const b = document.querySelector('.label-badge');
        return b && b.innerText.includes('Inconclusive');
      },
      { timeout: 30000 }
    );

    const badge2 = await page.$eval('.label-badge', el => el.innerText.trim());
    console.log(`Result badge: "${badge2}"`);

    const shot2 = path.join(SCREENSHOT_DIR, 'inconclusive.png');
    await page.screenshot({ path: shot2, fullPage: true });
    console.log(`Saved screenshot: ${shot2}`);

    // 4. Test Image 3: Unknown Product
    console.log('\n[4/8] Screening Image 3: Unknown Product (000010.jpg)...');
    await page.click('button.btn-secondary'); // Clear
    await new Promise(r => setTimeout(r, 400));

    const input3 = await page.$('#pill-file-input');
    await input3.uploadFile(FIXTURES.unknownProduct);
    await new Promise(r => setTimeout(r, 600));

    await page.click('button.btn-primary');
    await page.waitForFunction(
      () => {
        const b = document.querySelector('.label-badge');
        return b && b.innerText.includes('Unknown Product');
      },
      { timeout: 30000 }
    );

    const badge3 = await page.$eval('.label-badge', el => el.innerText.trim());
    console.log(`Result badge: "${badge3}"`);

    const shot3 = path.join(SCREENSHOT_DIR, 'unknown_product.png');
    await page.screenshot({ path: shot3, fullPage: true });
    console.log(`Saved screenshot: ${shot3}`);

    // 5. Test Image 4: Retake Required
    console.log('\n[5/8] Screening Image 4: Retake Required (retake_blank.jpg)...');
    await page.click('button.btn-secondary'); // Clear
    await new Promise(r => setTimeout(r, 400));

    const input4 = await page.$('#pill-file-input');
    await input4.uploadFile(FIXTURES.retakeBlank);
    await new Promise(r => setTimeout(r, 600));

    await page.click('button.btn-primary');
    await page.waitForFunction(
      () => {
        const b = document.querySelector('.label-badge');
        return b && b.innerText.includes('Retake Required');
      },
      { timeout: 30000 }
    );

    const badge4 = await page.$eval('.label-badge', el => el.innerText.trim());
    console.log(`Result badge: "${badge4}"`);

    const shot4 = path.join(SCREENSHOT_DIR, 'retake_required.png');
    await page.screenshot({ path: shot4, fullPage: true });
    console.log(`Saved screenshot: ${shot4}`);

    // 6. Test Non-Image and >10MB upload error handling
    console.log('\n[6/8] Testing error handling (non-image and >10MB)...');
    await page.click('button.btn-secondary'); // Clear
    await new Promise(r => setTimeout(r, 400));

    // Upload non-image
    const inputNonImg = await page.$('#pill-file-input');
    await inputNonImg.uploadFile(FIXTURES.notAnImage);
    await new Promise(r => setTimeout(r, 400));

    const nonImgError = await page.$eval('.error-box span', el => el.innerText.trim());
    console.log(`Non-image error message: "${nonImgError}"`);

    // Upload >10MB
    const inputLarge = await page.$('#pill-file-input');
    await inputLarge.uploadFile(FIXTURES.over10Mb);
    await new Promise(r => setTimeout(r, 400));

    const largeError = await page.$eval('.error-box span', el => el.innerText.trim());
    console.log(`Over 10MB error message: "${largeError}"`);

    // 7. Test About/Method Page
    console.log('\n[7/8] Testing About & Method Page...');
    // Click navigation tab for About & Method
    const tabs = await page.$$('.nav-tab');
    await tabs[1].click(); // Second tab is "Method & Evaluation"
    await new Promise(r => setTimeout(r, 500));

    const evalHeading = await page.$eval('.eval-table th', el => el.innerText.trim());
    console.log(`Evaluation table present with header: "${evalHeading}"`);

    const shot5 = path.join(SCREENSHOT_DIR, 'about_page.png');
    await page.screenshot({ path: shot5, fullPage: true });
    console.log(`Saved screenshot: ${shot5}`);

    // 8. Test Mobile Layout
    console.log('\n[8/8] Testing Mobile Responsive Layout (390x844)...');
    await page.click('.nav-tabs button:first-child');
    await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
    await new Promise(r => setTimeout(r, 400));

    // Screen an image directly on mobile view
    const inputMobile = await page.$('#pill-file-input');
    await inputMobile.uploadFile(FIXTURES.likelyGenuine);
    await new Promise(r => setTimeout(r, 500));

    await page.click('button.btn-primary');
    await page.waitForFunction(
      () => {
        const b = document.querySelector('.label-badge');
        return b && b.innerText.includes('Likely Genuine');
      },
      { timeout: 30000 }
    );
    await new Promise(r => setTimeout(r, 500));

    const shot6 = path.join(SCREENSHOT_DIR, 'mobile_layout.png');
    await page.screenshot({ path: shot6, fullPage: true });
    console.log(`Saved screenshot: ${shot6}`);

    console.log('\n====================================================');
    console.log('ALL VERIFICATIONS PASSED SUCCESSFULLY!');
    console.log('Screenshots saved to:', SCREENSHOT_DIR);
    console.log('====================================================');
  } catch (err) {
    console.error('Verification failed with error:', err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

run();
