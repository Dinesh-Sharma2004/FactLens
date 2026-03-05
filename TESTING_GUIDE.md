# Testing Guide: Tab Switching State Persistence

## How to Test the Solution

### Test Case 1: Analysis Continues While Switching Tabs

1. **Start Verification Analysis**
   - Click on "Verify Mode" tab (should already be selected)
   - Enter a claim or text: "The Earth is flat"
   - Click "Verify Now"
   - You should see "Analyzing..." with a spinner

2. **Switch to Summarization Mode**
   - While analysis is still running, click "Summarize Mode" tab
   - The verification analysis should **continue in the background**
   - The summarization tab should show empty (no previous submission)

3. **Switch Back to Verification Mode**
   - Click "Verify Mode" tab again
   - The **previous verification analysis results should be displayed**, not lost
   - The response text should be partially or fully completed

### Test Case 2: Independent State per Mode

1. **Start Verification Analysis**
   - In Verify Mode: Submit "The moon is made of cheese"
   - Wait for some response text to appear

2. **Start Summarization Analysis**
   - Switch to Summarize Mode
   - Enter a URL: "https://example.com/article"
   - Click "Verify Now"
   - You should see a different loading state for summarization

3. **Switch Between Modes**
   - Switch to Verify Mode → Should show verification results
   - Switch to Summarize Mode → Should show summarization results
   - Multiple switches: Both should preserve their own states

### Test Case 3: No State Loss on Multiple Submissions

1. **First Verification**
   - Verify Mode: Submit query1
   - Wait for results

2. **Switch to Summarization**
   - Submit a summarization request
   - Wait for results (partial or complete)

3. **Switch Back to Verify**
   - Verify Mode results from step 1 should still be visible

4. **Submit New Verification**
   - Enter a new claim
   - Click "Verify Now"
   - New analysis should start while old one is replaced
   - Switching to Summarize and back should show the new results

### Test Case 4: Audio Input State Preservation (Verify Mode Only)

1. **Record Audio in Verify Mode**
   - Click the microphone icon
   - Record some speech
   - Audio should be transcribed and added to the input field
   - Results from previous verification should be preserved

2. **Switch to Summarize and Back**
   - Switch to Summarize Mode → Audio transcribed text stays in query
   - Switch back to Verify Mode → Same audio-transcribed content is still there

## Expected Behavior After Fix

✅ Analysis continues running when you switch tabs
✅ Previous analysis results persist when you switch back
✅ Each mode (verify/summarize) has independent state
✅ Switching tabs doesn't clear the query input or results
✅ No console errors related to stale state or request sequences
✅ Audio transcription works correctly across mode switches

## What to Watch For

🔍 Console errors - Use DevTools (F12) to check for any errors
🔍 Loading indicators - Should match the active mode being analyzed
🔍 Results display - Should show the correct mode's results
🔍 Input field - Should maintain its value when switching back to the same mode
