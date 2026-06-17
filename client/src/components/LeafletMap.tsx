import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useRef } from "react";
import { stationData } from "@/lib/stationsData";
import { cn } from "@/lib/utils";

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = 6371;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

/** Indicative representativeness reach: half the distance to the nearest station. */
function nearestNeighborKm(station: { lat: number; lon: number; siteId: string }) {
  let nearest = Infinity;
  stationData.forEach((other) => {
    if (other.siteId === station.siteId) return;
    const d = haversineKm(station.lat, station.lon, other.lat, other.lon);
    if (d < nearest) nearest = d;
  });
  return Number.isFinite(nearest) ? nearest : 0;
}

interface LeafletMapProps {
  className?: string;
}

export function LeafletMap({ className }: LeafletMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = L.map(container.current, {
      center: [-46.3, -70.4],
      zoom: 4,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    stationData.forEach((station) => {
      // Representativeness reach overlay: a translucent disc whose radius is
      // half the distance to the nearest station (geographic scope proxy).
      const reachKm = nearestNeighborKm(station) / 2;
      if (reachKm > 0) {
        L.circle([station.lat, station.lon] as [number, number], {
          radius: reachKm * 1000,
          color: station.qualityColor,
          weight: 1,
          opacity: 0.5,
          fillColor: station.qualityColor,
          fillOpacity: 0.07,
        }).addTo(map);
      }

      const size = Math.max(station.markerRadius * 2.6, 22);

      const icon = L.divIcon({
        html: `<div style="
          background:${station.qualityColor};
          width:${size}px;height:${size}px;
          border-radius:50%;border:2px solid white;
          display:flex;align-items:center;justify-content:center;
          font-size:9px;font-weight:700;color:white;font-family:sans-serif;
          box-shadow:0 4px 14px rgba(0,0,0,0.28);
        ">${station.siteId.replace("-", "")}</div>`,
        className: "",
        iconSize: [size, size] as [number, number],
        iconAnchor: [size / 2, size / 2] as [number, number],
        popupAnchor: [0, -(size / 2 + 4)] as [number, number],
      });

      const popup = L.popup({ maxWidth: 280 }).setContent(`
        <div style="color:#213126;font-family:sans-serif;">
          <div style="font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:${station.qualityColor};font-weight:700;margin-bottom:8px;">${station.siteId}</div>
          <div style="font-size:18px;font-weight:700;margin-bottom:6px;line-height:1.2;">${station.siteName}</div>
          <div style="font-size:12px;color:#506053;margin-bottom:10px;">${station.country} · ${station.ecosystem}</div>
          <div style="font-size:12px;line-height:1.8;color:#374338;">
            <strong>Coverage:</strong> ${station.yearStart}–${station.yearEnd}<br/>
            <strong>Observations:</strong> ${formatNumber(station.observations)}<br/>
            <strong>Utility score:</strong> ${station.utilityScore.toFixed(3)}<br/>
            <strong>Valid NEE:</strong> ${station.validNeePct.toFixed(1)}%<br/>
            <strong>Variables:</strong> ${station.variablesPresent.join(", ")}
          </div>
        </div>
      `);

      L.marker([station.lat, station.lon] as [number, number], { icon })
        .bindPopup(popup)
        .addTo(map);
    });

    const bounds = L.latLngBounds(
      stationData.map((s) => [s.lat, s.lon] as [number, number])
    );
    map.fitBounds(bounds, { padding: [60, 60] });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={container} className={cn("w-full h-[500px]", className)} />;
}
