const https = require('https');
const fs = require('fs');
const path = require('path');

const cities = [
    { name: 'paris', folder: 'public/assets/card-images/paris', query: 'paris-eiffel-tower' },
    { name: 'tokyo', folder: 'public/assets/card-images/tokyo', query: 'tokyo-japan' },
    { name: 'barcelona', folder: 'public/assets/card-images/barcelona', query: 'barcelona-spain' },
    { name: 'london', folder: 'public/assets/card-images/london', query: 'london-uk' },
    { name: 'dubai', folder: 'public/assets/card-images/dubai', query: 'dubai-uae' },
    { name: 'newyork', folder: 'public/assets/card-images/newyork', query: 'new-york-city' }
];

// Create directories
cities.forEach(city => {
    const dir = path.join(__dirname, city.folder);
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        console.log(`Created directory: ${dir}`);
    }
});

// Download image function
function downloadImage(url, filepath) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(filepath);
        https.get(url, (response) => {
            // Follow redirects
            if (response.statusCode === 301 || response.statusCode === 302) {
                return downloadImage(response.headers.location, filepath).then(resolve).catch(reject);
            }

            response.pipe(file);
            file.on('finish', () => {
                file.close();
                console.log(`Downloaded: ${filepath}`);
                resolve();
            });
        }).on('error', (err) => {
            fs.unlink(filepath, () => { });
            reject(err);
        });
    });
}

// Download images for each city
async function downloadAllImages() {
    console.log('Starting image downloads...\n');

    for (const city of cities) {
        console.log(`Downloading images for ${city.name}...`);

        for (let i = 1; i <= 4; i++) {
            let querySuffix = '';

            if (i === 2) {
                querySuffix = ',portrait';
            }
            if (i === 4) {
                querySuffix = ',vertical';
            }

            const url = `https://source.unsplash.com/random/?${city.query}${querySuffix}&w=600&sig=${i}`;
            const filepath = path.join(__dirname, city.folder, `${i}.png`);

            try {
                await downloadImage(url, filepath);
                await new Promise(resolve => setTimeout(resolve, 1000));
            } catch (error) {
                console.error(`Error downloading ${city.name} image ${i}:`, error.message);
            }
        }
        console.log(`Completed ${city.name}\n`);
    }

    console.log('All downloads complete!');
}

downloadAllImages();
