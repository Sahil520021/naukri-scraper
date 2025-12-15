/**
 * Naukri Resdex CV Scraper - Apify Actor
 * Calls Python scraper service for robust async scraping
 */

import { Actor } from 'apify';
import axios from 'axios';

// Configuration
const CONFIG = {
    pythonScraperUrl: process.env.PYTHON_SCRAPER_URL || 'http://localhost:8000/scrape',
    timeout: 600000  // 10 minutes
};

await Actor.init();

try {
    // ========== START ==========
    console.log('='.repeat(60));
    console.log('🚀 NAUKRI CV SCRAPER STARTED (Async Python Backend)');
    console.log('='.repeat(60));

    // Get input from user
    const input = await Actor.getInput();
    const { curlCommand, maxResults = 10 } = input;

    // Internal concurrency setting (hidden from user input as requested)
    const INTERNAL_CONCURRENCY = 10;

    // Validate required inputs
    if (!curlCommand) {
        throw new Error('❌ cURL command is required. Please provide the complete cURL command from Chrome DevTools.');
    }

    console.log(`📊 Requested profiles: ${maxResults}`);
    console.log(`🌐 Backend URL: ${CONFIG.pythonScraperUrl}`);
    console.log(`⏰ Started at: ${new Date().toISOString()}`);
    console.log('');
    console.log('📡 Calling Python scraper service...');

    const startTime = Date.now();

    // 2. Setup Proxy
    const proxyConfig = await Actor.createProxyConfiguration(input.proxyConfiguration);
    let proxyUrl = null;
    if (proxyConfig) {
        proxyUrl = await proxyConfig.newUrl();
        console.log(`🔒 Using Proxy: ${proxyUrl.split('@')[1] || 'Authenticated'}`); // Log safe part
    } else {
        console.log('⚠️  No Proxy configured! Running on Datacenter IP (Risk of blocking).');
    }

    // Call Python scraper service
    const response = await axios.post(
        CONFIG.pythonScraperUrl,
        {
            curlCommand: curlCommand,
            maxResults: maxResults,
            concurrency: INTERNAL_CONCURRENCY,
            proxyUrl: proxyUrl
        },
        {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: CONFIG.timeout
        }
    );

    console.log('✅ Python scraper completed execution');
    console.log('');

    const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(1);
    const result = response.data;

    if (!result.success) {
        throw new Error(`Scraper reported failure: ${result.error}`);
    }

    // Parse results using Python scraper schema
    const actualCount = result.totalCandidates || 0;
    const candidates = result.candidates || [];
    const debugInfo = result.debug_info || {};
    const failedCount = debugInfo.total_failed || 0;

    // Push data
    if (actualCount > 0) {
        console.log(`📊 Processing ${actualCount} candidates from backend`);
        await Actor.pushData(candidates);
    }

    // Save Output
    await Actor.setValue('OUTPUT', result);

    // ========== RESULTS ANALYSIS ==========
    console.log('');
    console.log('='.repeat(60));
    console.log('📈 SCRAPING RESULTS');
    console.log('='.repeat(60));
    console.log(`✅ Profiles received: ${actualCount}`);
    console.log(`⚠️  Profiles failed:   ${failedCount}`);
    console.log(`🎯 Profiles requested: ${maxResults}`);
    console.log(`⏱️  Time taken: ${elapsedTime}s`);
    console.log('');

    // ========== QUOTA/LIMIT DETECTION ==========
    const shortfall = maxResults - actualCount;

    if (shortfall > 0 && actualCount > 0) {
        const percentageGot = ((actualCount / maxResults) * 100).toFixed(1);

        console.log('⚠️  ATTENTION: Did not get all requested profiles');
        console.log('─'.repeat(60));
        console.log(`   Missing: ${shortfall} profiles (got ${percentageGot}%)`);
        console.log('');
        console.log('💡 Possible reasons:');

        if (actualCount % 50 === 0) {
            const pagesGot = actualCount / 50;
            const pagesRequested = Math.ceil(maxResults / 50);
            console.log(`   📄 Got ${pagesGot} pages out of ${pagesRequested} requested pages`);
            console.log('      • Naukri CV viewing quota exhausted');
            console.log('      • Daily/monthly limit reached');
        } else {
            console.log('   📊 Partial success - Possible causes:');
            console.log('      • Session timeout or network issues');
            console.log('      • CAPTCHA triggered');
        }

        console.log('');
        console.log('🔧 Recommended actions:');
        console.log('   1. Login to Naukri Resdex and check CV viewing quota');
        console.log('   2. Get fresh cookies (new cURL command)');
        console.log('');

    } else if (actualCount === 0) {
        console.log('❌ CRITICAL: No profiles scraped!');
        console.log('─'.repeat(60));
        console.log('💡 Likely causes:');
        console.log('   ❌ Cookies expired - Get fresh cURL from Chrome DevTools');
        console.log('   ❌ Account quota fully exhausted');
        console.log('');
        console.log('🔧 Immediate actions:');
        console.log('   1. Open Naukri Resdex in Chrome incognito mode');
        console.log('   2. Perform a search');
        console.log('   3. Copy fresh cURL command from Network tab');
        console.log('');
    } else {
        console.log('✅ SUCCESS: Got all requested profiles!');
        console.log('');
    }

    // ========== SAVE STATS ==========
    await Actor.setValue('SCRAPING_STATS', {
        requested: maxResults,
        received: actualCount,
        failed: failedCount,
        shortfall: shortfall,
        successRate: `${((actualCount / maxResults) * 100).toFixed(1)}%`,
        timeTakenSeconds: parseFloat(elapsedTime),
        timestamp: new Date().toISOString(),
        quotaExhausted: shortfall > 0
    });

    // ========== FINAL SUMMARY ==========
    console.log('='.repeat(60));
    console.log('🎉 ACTOR FINISHED');
    console.log('='.repeat(60));

} catch (error) {
    // ========== ERROR HANDLING ==========
    console.error('');
    console.error('='.repeat(60));
    console.error('❌ SCRAPING FAILED');
    console.error('='.repeat(60));
    console.error(`❌ Error: ${error.message}`);

    if (error.response?.data) {
        console.error('');
        console.error('📋 Backend Error details:');
        console.error(JSON.stringify(error.response.data, null, 2));
    }

    console.error('');

    if (error.code === 'ECONNREFUSED') {
        console.error('💡 Fix: Python backend is not accessible');
        console.error('   • Check Docker container is running');
    } else if (error.code === 'ETIMEDOUT') {
        console.error('💡 Fix: Request timed out');
        console.error('   • Reduce maxResults');
        console.error('   • Increase timeout');
    }

    console.error('');
    console.error('='.repeat(60));
    throw error;
}

await Actor.exit();
