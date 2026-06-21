"use client";

import React, { useEffect, useState } from "react";
import { X, Navigation, MapPin } from "lucide-react";
import "leaflet/dist/leaflet.css";

// Dynamically import Leaflet components to avoid SSR failures in Next.js
let MapContainer, TileLayer, Marker, Popup;
if (typeof window !== "undefined") {
  // Require react-leaflet components client-side
  const reactLeaflet = require("react-leaflet");
  MapContainer = reactLeaflet.MapContainer;
  TileLayer = reactLeaflet.TileLayer;
  Marker = reactLeaflet.Marker;
  Popup = reactLeaflet.Popup;
  
  // Resolve default marker icon issues in Leaflet with Next.js
  const L = require("leaflet");
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png",
    iconUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png",
    shadowUrl: "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
  });
}

export default function MapDrawer({ isOpen, onClose, destination, itinerary }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen) return null;

  // Mock coordinates for major destinations
  const getCoordinates = (dest) => {
    const d = dest?.toLowerCase() || "";
    if (d.includes("bali")) return [-8.4095, 115.1889]; // Bali
    if (d.includes("tokyo")) return [35.6762, 139.6503]; // Tokyo
    if (d.includes("paris")) return [48.8566, 2.3522]; // Paris
    if (d.includes("rome")) return [41.9028, 12.4964]; // Rome
    if (d.includes("london")) return [51.5074, -0.1278]; // London
    if (d.includes("sydney")) return [-33.8688, 151.2093]; // Sydney
    return [-8.4095, 115.1889]; // Default: Bali
  };

  const centerCoords = getCoordinates(destination);

  // Extract markers from itinerary activities if they have locations
  const getMarkers = () => {
    if (!itinerary || !itinerary.days) return [];
    
    const markers = [];
    let count = 0;
    itinerary.days.forEach((day) => {
      day.activities?.forEach((act) => {
        // Add coordinates slightly offset from center for demonstration
        const offsetLat = (Math.random() - 0.5) * 0.08;
        const offsetLng = (Math.random() - 0.5) * 0.08;
        markers.push({
          id: count++,
          title: act.title,
          description: act.description,
          coords: [centerCoords[0] + offsetLat, centerCoords[1] + offsetLng]
        });
      });
    });
    return markers;
  };

  const mapMarkers = getMarkers();

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-end bg-slate-900/50 backdrop-blur-sm transition-all duration-300">
      {/* Drawer Body */}
      <div className="w-[500px] h-[95vh] bg-surface rounded-l-3xl p-6 mr-4 pink-shadow flex flex-col gap-4 relative overflow-hidden border border-pink-100">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-pink-50 hover:bg-pink-100 rounded-full text-primary transition-all bouncy-hover z-10"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2">
          <Navigation className="w-5 h-5 text-accent animate-pulse" />
          <div>
            <h3 className="text-sm font-extrabold text-secondary">Interactive Map Overlay</h3>
            <p className="text-[10px] text-muted font-bold">Showing markers for: {destination || "Bali"}</p>
          </div>
        </div>

        {/* Map Container */}
        <div className="flex-1 bg-pink-50/20 border-2 border-pink-100 rounded-2xl overflow-hidden relative min-h-[400px]">
          {mounted && MapContainer ? (
            <MapContainer
              center={centerCoords}
              zoom={11}
              scrollWheelZoom={true}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {mapMarkers.map((marker) => (
                <Marker key={marker.id} position={marker.coords}>
                  <Popup>
                    <div className="p-1 max-w-[200px]">
                      <h4 className="text-xs font-bold text-secondary mb-1 flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
                        {marker.title}
                      </h4>
                      <p className="text-[10px] text-muted leading-relaxed font-medium">{marker.description}</p>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-2.5">
              <span className="w-8 h-8 rounded-full border-4 border-t-primary border-pink-100 animate-spin" />
              <p className="text-xs font-bold text-muted">Spinning up Leaflet Map...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
