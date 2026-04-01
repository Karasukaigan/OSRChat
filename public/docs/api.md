## GET /api/version

Retrieve the application version.

**Example Response:**
```json
{ "version": "OSRChat v1.4.1" }
```

---

## POST /api/script

Load Funscript script data.

**Request Body (JSON):** Full Funscript file content, which must include the `actions` field.

**Response:** Result of script loading.

---

## GET /api/script/play?at=0

Start playing the script from the specified time (in milliseconds).

---

## GET /api/script/stop

Stop the currently playing script.

---

## POST /api/script/custom

Generate and play a script using a custom motion pattern.

**Request Body (JSON) Fields:**
- `range`: Motion range limit, default is 100  
- `inverted`: Whether to invert the motion, default is False  
- `max_pos`: Maximum position, default is 100  
- `min_pos`: Minimum position, default is 0  
- `freq`: Frequency, default is 1.0  
- `decline_ratio`: Decline phase ratio, default is 0.5 (i.e., triangular waveform)  
- `start_pos`: Starting position, default is None  
- `loop_count`: Number of loops, default is 100  
- `custom_actions`: Custom `actions` array; if provided, it overrides all other settings except `loop_count`, default is None  

---

## GET /api/offset?ms=100

Adjust the global time offset in milliseconds.

**Parameters:**
- `ms`: Offset adjustment value (not the total offset), integer, can be positive or negative

**Example Response:**
```json
{
  "message": "Offset adjusted successfully",
  "old_offset": 0,
  "new_offset": 100,
  "adjustment": 100
}
```

---

## Support Development

This project is free and open source, developed and maintained in my spare time by [me](https://github.com/Karasukaigan). If you find it helpful or inspiring, please consider supporting its continued development.

Your donation helps cover development time, feature improvements, and maintenance costs.

| Ethereum |
|:---|
| `0x3E709387db900c47C6726e4CFa40A5a51bC9Fb97` |
| <img src="img/Ethereum.png" alt="Ethereum" width="150"> |

| Bitcoin |
|:---|
| `bc1qguk59xapemd3k0a8hen229av3vs5aywq9gzk6e` |
| <img src="img/Bitcoin.png" alt="Bitcoin" width="150"> |

Every contribution, no matter the amount, is greatly appreciated. Thank you for supporting open-source!
