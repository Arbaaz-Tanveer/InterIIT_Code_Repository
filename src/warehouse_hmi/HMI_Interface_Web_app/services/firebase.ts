import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, User } from 'firebase/auth';
import { getFirestore, collection, addDoc, query, orderBy, onSnapshot, Timestamp, limit, writeBatch, doc, where, getDocs } from 'firebase/firestore';
import { ScannedData } from '../types';

// --------------------------------------------------------
// TODO: PASTE YOUR FIREBASE CONFIGURATION BELOW
// You get this from the Firebase Console -> Project Settings
// --------------------------------------------------------
const firebaseConfig = {
  apiKey: "AIzaSyC3iyAFotIT9ziJpkSekfp9a5QpG8BMcBo",
  authDomain: "testingpurpose-a.firebaseapp.com",
  projectId: "testingpurpose-a",
  storageBucket: "testingpurpose-a.firebasestorage.app",
  messagingSenderId: "333114784648",
  appId: "1:333114784648:web:80fbc2eb70c91c976f583d",
  measurementId: "G-VLBPZWEQ0N"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();

/**
 * Sign in with Google Popup
 */
export const loginWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (error) {
    console.error("Error logging in", error);
    throw error;
  }
};

/**
 * Log out
 */
export const logoutUser = async () => {
  await signOut(auth);
};

/**
 * Save a robot scan to Firestore
 */
export const saveScanLog = async (scanData: Omit<ScannedData, 'id'>) => {
  try {
    const docRef = await addDoc(collection(db, 'scan_logs'), {
      ...scanData,
      timestamp: Timestamp.now(), // Use server timestamp
      createdAt: Timestamp.now()
    });
    console.log("✅ Scan saved to Firestore with ID:", docRef.id, scanData);
  } catch (e) {
    console.error("❌ Error saving scan to Firestore:", e);
    throw e;
  }
};

/**
 * Subscribe to the latest logs
 */
export const subscribeToLogs = (callback: (logs: ScannedData[]) => void) => {
  const q = query(
    collection(db, 'scan_logs'),
    orderBy('timestamp', 'desc'),
    limit(50)
  );

  const unsubscribe = onSnapshot(q, (querySnapshot) => {
    const logs: ScannedData[] = [];
    querySnapshot.forEach((doc) => {
      const data = doc.data();
      // Convert Firestore Timestamp to string for UI
      const date = data.timestamp?.toDate ? data.timestamp.toDate() : new Date();

      logs.push({
        id: doc.id,
        rackId: data.rackId,
        content: data.content,
        category: data.category,
        timestamp: date.toISOString()
      });
    });
    console.log(`📊 Loaded ${logs.length} logs from Firestore`);
    callback(logs);
  });

  return unsubscribe;
};

/**
 * Delete multiple scans by their IDs
 */
export const deleteScans = async (ids: string[]): Promise<{ success: number; failed: number }> => {
  const batch = writeBatch(db);
  let success = 0;
  let failed = 0;

  try {
    ids.forEach((id) => {
      const docRef = doc(db, 'scan_logs', id);
      batch.delete(docRef);
    });

    await batch.commit();
    success = ids.length;
    console.log(`✅ Successfully deleted ${success} scans`);
  } catch (error) {
    console.error('❌ Error deleting scans:', error);
    failed = ids.length;
  }

  return { success, failed };
};

/**
 * Delete scans within a date range
 */
export const deleteScansByDateRange = async (startDate: Date, endDate: Date): Promise<{ success: number; failed: number }> => {
  try {
    const startTimestamp = Timestamp.fromDate(startDate);
    const endTimestamp = Timestamp.fromDate(endDate);

    const q = query(
      collection(db, 'scan_logs'),
      where('timestamp', '>=', startTimestamp),
      where('timestamp', '<=', endTimestamp)
    );

    const querySnapshot = await getDocs(q);
    const batch = writeBatch(db);

    querySnapshot.forEach((doc) => {
      batch.delete(doc.ref);
    });

    await batch.commit();
    const count = querySnapshot.size;
    console.log(`✅ Successfully deleted ${count} scans in date range`);
    return { success: count, failed: 0 };
  } catch (error) {
    console.error('❌ Error deleting scans by date range:', error);
    return { success: 0, failed: 1 };
  }
};

