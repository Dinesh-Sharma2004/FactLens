# Implementation Details: State Separation Architecture

## File Modified
- `frontend/src/App.jsx`

## Key Architecture Changes

### 1. State Structure Before (❌ Problem)
```javascript
// Individual state variables - ALL cleared on mode change
const [query, setQuery] = useState("");
const [response, setResponse] = useState("");
const [meta, setMeta] = useState(null);
const [submittedInput, setSubmittedInput] = useState("");
const [loading, setLoading] = useState(false);
const [mediaStatus, setMediaStatus] = useState("");

// This useEffect cleared EVERYTHING on mode change
useEffect(() => {
  setQuery("");
  setResponse("");
  setMeta(null);
  setLoading(false);
  setMediaStatus("");
}, [mode]); // ❌ All state lost when mode changes
```

### 2. State Structure After (✅ Solution)
```javascript
// Single source of truth - separates state by mode
const [modeData, setModeData] = useState({
  verify: {
    query: "",
    response: "",
    meta: null,
    submittedInput: "",
    loading: false,
    mediaStatus: "",
    abortController: null,
    requestSeq: 0,
  },
  summarize: {
    query: "",
    response: "",
    meta: null,
    submittedInput: "",
    loading: false,
    mediaStatus: "",
    abortController: null,
    requestSeq: 0,
  },
});

// Always points to current mode's data
const currentData = modeData[mode];

// NO useEffect that clears state - state is preserved automatically!
// Switching mode just changes which modeData[mode] we read from
```

### 3. Helper Functions for Mode-Specific Updates

```javascript
// Updates only current mode's data
const setCurrentModeData = (updates) => {
  setModeData((prev) => ({
    ...prev,
    [mode]: {
      ...prev[mode],
      ...updates,
    },
  }));
};

// Individual setters that work with current mode
const setQuery = (value) => {
  setCurrentModeData({ 
    query: typeof value === "function" ? value(currentData.query) : value 
  });
};

const setResponse = (value) => {
  setCurrentModeData({ 
    response: typeof value === "function" ? value(currentData.response) : value 
  });
};

// ... similar for setMeta, setLoading, setMediaStatus, etc.
```

### 4. Request Sequence Tracking

```javascript
// Each mode tracks its own request sequence
const newSeq = currentData.requestSeq + 1;
setRequestSeq(newSeq);

// Stale check prevents cross-mode response mixing
const stale = newSeq !== modeData[modeAtSubmit].requestSeq || 
              modeRef.current !== modeAtSubmit;
if (stale) return; // Ignore callbacks from old requests

// Update only the mode that submitted the request
setModeData((prev) => ({
  ...prev,
  [modeAtSubmit]: {
    ...prev[modeAtSubmit],
    response: prev[modeAtSubmit].response + chunk.data,
  },
}));
```

### 5. Abort Controller Management

```javascript
// Each mode maintains its own abort controller
if (currentData.abortController) {
  currentData.abortController.abort();
}

const controller = new AbortController();
setAbortController(controller); // Sets only for current mode

// Cleanup in finally block
finally {
  setModeData((prev) => {
    if (prev[modeAtSubmit].abortController === controller) {
      return {
        ...prev,
        [modeAtSubmit]: {
          ...prev[modeAtSubmit],
          abortController: null,
        },
      };
    }
    return prev;
  });
}
```

## Flow Diagram

```
User Interface Layer
    ↓
currentData = modeData[mode]  ← Always fresh current mode data
    ↓
[Verify] [Summarize] buttons
    ↓
setMode("verify") or setMode("summarize")
    ↓
What changes? mode variable
What stays? modeData[verify] and modeData[summarize] are preserved!
    ↓
currentData automatically points to new mode's data
    ↓
UI re-renders with currentData values
    ↓
All previous mode's data is preserved for when switching back
```

## Benefits of This Approach

1. **Data Persistence**: Each mode's state is never cleared
2. **Independent Analysis**: Multiple modes can analyze simultaneously
3. **Clean Switching**: Tab switching is instant (no state clearing)
4. **Request Isolation**: Responses from old requests don't update wrong mode
5. **Backward Compatible**: Same setter function signatures as before
6. **Scalable**: Easy to add more modes without refactoring
7. **Memory Safe**: Proper cleanup with abort controllers

## Performance Considerations

- Single `modeData` state object (same as before, just organized differently)
- `setModeData` only updates current mode's properties (efficient)
- No unnecessary re-renders due to React's memo and useMemo
- Abort controllers prevent network requests from running unnecessarily
- Request sequence tracking prevents stale updates
