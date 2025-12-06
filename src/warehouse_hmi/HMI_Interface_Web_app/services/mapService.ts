import { collection, getDocs, addDoc, deleteDoc, doc, updateDoc } from 'firebase/firestore';
import { MapData } from '../types';
import { db } from './firebase';

const MAPS_COLLECTION = 'maps';

export const mapService = {
    async getAllMaps(): Promise<MapData[]> {
        try {
            const querySnapshot = await getDocs(collection(db, MAPS_COLLECTION));
            console.log("🔥 Firestore query returned", querySnapshot.docs.length, "documents");
            const maps = querySnapshot.docs.map(doc => {
                const data = doc.data();
                console.log("🔥 Document ID:", doc.id, "Stored data:", data);
                // IMPORTANT: Assign id AFTER spreading data to ensure document ID overrides any stored id field
                const map = {
                    ...data,
                    id: doc.id  // Document ID always takes precedence
                } as MapData;
                console.log("🔥 Final map object:", { name: map.name, id: map.id });
                return map;
            });
            console.log("🔥 All processed maps:", maps.map(m => ({ name: m.name, id: m.id })));
            return maps;
        } catch (error) {
            console.error("Error getting maps: ", error);
            return [];
        }
    },

    async saveMap(mapData: Omit<MapData, 'id'>): Promise<string> {
        try {
            const docRef = await addDoc(collection(db, MAPS_COLLECTION), {
                ...mapData,
                createdAt: Date.now(),
                updatedAt: Date.now()
            });
            return docRef.id;
        } catch (error) {
            console.error("Error adding map: ", error);
            throw error;
        }
    },

    async updateMap(id: string, mapData: Partial<MapData>): Promise<void> {
        try {
            const mapRef = doc(db, MAPS_COLLECTION, id);
            await updateDoc(mapRef, {
                ...mapData,
                updatedAt: Date.now()
            });
        } catch (error) {
            console.error("Error updating map: ", error);
            throw error;
        }
    },

    async deleteMap(id: string): Promise<void> {
        try {
            await deleteDoc(doc(db, MAPS_COLLECTION, id));
        } catch (error) {
            console.error("Error deleting map: ", error);
            throw error;
        }
    },

    // Set default map (stored in localStorage)
    setDefaultMap(mapId: string): void {
        localStorage.setItem('defaultMapId', mapId);
        console.log(`✅ Set default map to: ${mapId}`);
    },

    // Get default map ID
    getDefaultMapId(): string | null {
        return localStorage.getItem('defaultMapId');
    },

    // Clear default map
    clearDefaultMap(): void {
        localStorage.removeItem('defaultMapId');
        console.log('✅ Cleared default map');
    }
};
