# Final Database (Cassandra) vs AI Analytics Comparison Report

## System Health Check
{
  "status": "online",
  "records_indexed": 10,
  "model": "all-MiniLM-L6-v2",
  "database": "/Users/logicfocus/.gemini/antigravity/scratch/ai_vehicle_analytics/vehicles.db"
}

---

### 1. Specific Vehicle Tracking
**Query**: `TN09AB105 movements on 2026-01-29`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |
| **Cassandra** | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | - |
| *AI Result* | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | ✅ 0.4764 |

---

### 2. Semantic Location Discovery
**Query**: `vehicles at Location_6 yesterday`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |
| **Cassandra** | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | - |
| *AI Result* | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | ✅ 0.6015 |

---

### 3. Explicit Historical Search (YYYY-MM-DD)
**Query**: `all traffic on 2026-01-29`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |
| **Cassandra** | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | - |
| **Cassandra** | TN09AB101 | Location_2 | 2026-01-29 08:35:20 | CAM_2 | Camera_2 | /snapshots/car_2.jpg | /videos/car_2.mp4 | - |
| **Cassandra** | TN09AB102 | Location_3 | 2026-01-29 10:30:00 | CAM_3 | Camera_3 | /snapshots/car_3_2.jpg | /videos/car_3_2.mp4 | - |
| **Cassandra** | TN09AB104 | Location_5 | 2026-01-29 11:15:00 | CAM_5 | Camera_5 | /snapshots/car_5.jpg | /videos/car_5.mp4 | - |
| **Cassandra** | TN09AB109 | Location_10 | 2026-01-29 17:15:20 | CAM_10 | Camera_10 | /snapshots/car_10.jpg | /videos/car_10.mp4 | - |
| *AI Result* | TN09AB105 | Location_6 | 2026-01-29 08:30:20 | CAM_6 | Camera_6 | /snapshots/car_6.jpg | /videos/car_6.mp4 | ✅ 0.3945 |
| *AI Result* | TN09AB101 | Location_2 | 2026-01-29 08:35:20 | CAM_2 | Camera_2 | /snapshots/car_2.jpg | /videos/car_2.mp4 | ✅ 0.3365 |
| *AI Result* | TN09AB102 | Location_3 | 2026-01-29 10:30:00 | CAM_3 | Camera_3 | /snapshots/car_3_2.jpg | /videos/car_3_2.mp4 | ✅ 0.3537 |
| *AI Result* | TN09AB104 | Location_5 | 2026-01-29 11:15:00 | CAM_5 | Camera_5 | /snapshots/car_5.jpg | /videos/car_5.mp4 | ✅ 0.3487 |
| *AI Result* | TN09AB109 | Location_10 | 2026-01-29 17:15:20 | CAM_10 | Camera_10 | /snapshots/car_10.jpg | /videos/car_10.mp4 | ✅ 0.3547 |

---

### 4. Unknown Vehicle Detection
**Query**: `List of unknown vehicles spotted in warehouse`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |

---

### 5. Localized Date Format (DD/MM/YYYY)
**Query**: `all vehicles that entered Location_6 on 30/1/2026`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |
| **Cassandra** | TN09AB105 | Location_6 | 2026-01-30 10:00:20 | CAM_6 | Camera_6 | /snapshots/car_6_2.jpg | /videos/car_6_2.mp4 | - |
| **Cassandra** | TN09AB105 | Location_6 | 2026-01-30 13:00:00 | CAM_6 | Camera_6 | /snapshots/car_6_3.jpg | /videos/car_6_3.mp4 | - |
| *AI Result* | TN09AB105 | Location_6 | 2026-01-30 10:00:20 | CAM_6 | Camera_6 | /snapshots/car_6_2.jpg | /videos/car_6_2.mp4 | ✅ 0.5520 |
| *AI Result* | TN09AB105 | Location_6 | 2026-01-30 13:00:00 | CAM_6 | Camera_6 | /snapshots/car_6_3.jpg | /videos/car_6_3.mp4 | ✅ 0.5455 |

---

### 6. Semantic Suspicious Activity (Last 2 Days)
**Query**: `show suspicious activities in last 2 days`

| Source | vehicle_no | location | timestamp | camera_id | camera_name | snapshotpath | videopath | Score |
| **Cassandra** | TN09AB107 | Location_8 | 2026-01-30 03:15:00 | CAM_8 | Camera_8 | /snapshots/car_8.jpg | /videos/car_8.mp4 | - |
| *AI Result* | TN09AB107 | Location_8 | 2026-01-30 03:15:00 | CAM_8 | Camera_8 | /snapshots/car_8.jpg | /videos/car_8.mp4 | ✅ 0.2917 |

---

