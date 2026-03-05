# State Persistence Solution for Tab Switching

## Problem
When switching between "Verification" and "Summarization" tabs, the state was being completely cleared, causing:
- Active analysis to be lost
- Previous results to disappear when switching back to the same tab
- User experience being disrupted

## Root Cause
The `App.jsx` had a `useEffect` that cleared all state whenever the `mode` changed:
```javascript
useEffect(() => {
  // Clears ALL state on mode change
  setQuery("");
  setResponse("");
  setMeta(null);
  setLoading(false);
  setMediaStatus("");
}, [mode]);
```

## Solution
Implemented separate state management for each mode:

### Key Changes in `App.jsx`:

1. **Separate State Structure**
   - Created a `modeData` state object containing separate state for both "verify" and "summarize" modes
   - Each mode maintains its own: `query`, `response`, `meta`, `submittedInput`, `loading`, `mediaStatus`, `abortController`, and `requestSeq`

2. **Current Mode Data**
   - `currentData = modeData[mode]` - Always points to the current mode's state
   - Automatically updates when mode changes without clearing data

3. **Setter Functions**
   - Created individual setters (`setQuery`, `setResponse`, etc.) that update only the current mode's state
   - Setters support both direct values and callback functions (for React patterns like `setState(prev => ...)`

4. **Mode-Specific Analysis**
   - Analysis continues in the background even when switching modes
   - Each mode maintains its own request sequence and abort controller
   - Stale request detection prevents outdated responses from updating the wrong mode

### How It Works Now:

1. **Submit in Verification Mode**
   - User submits a claim for verification
   - Analysis starts and saves state in `modeData.verify`

2. **Switch to Summarization Mode**
   - Previous verification analysis continues in background
   - `modeData.verify` state is preserved (but hidden from UI)
   - Fresh `modeData.summarize` state is shown (empty until user submits)

3. **Switch Back to Verification Mode**
   - Previous verification analysis is displayed again
   - User can see the completed results without losing data

4. **Submit in Summarization Mode**
   - New analysis for summarization mode starts
   - Saved independently from verification state
   - Can switch back to verification without losing summarization progress

## Benefits
✅ Analysis continues even when switching tabs
✅ Each mode maintains independent state
✅ No data loss when switching between modes
✅ Seamless user experience with multiple concurrent analyses
✅ Proper cleanup when components unmount or on errors
