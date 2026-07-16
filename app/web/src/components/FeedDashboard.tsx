"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { FeedSummary, FeedValidation } from "@/lib/types";
import { ROUTE_TYPE_NAMES } from "@/lib/types";

interface Props {
  summary: FeedSummary;
  validation: FeedValidation;
}

function formatTime(t: string | undefined): string {
  if (!t) return "-";
  const parts = t.split(":");
  if (parts.length !== 3) return t;
  const hour = parseInt(parts[0], 10);
  const minute = parts[1];
  if (hour >= 24) {
    const real = hour - 24;
    const period = real < 12 ? "AM" : "PM";
    const display = real === 0 ? 12 : real > 12 ? real - 12 : real;
    return `${display}:${minute} ${period} (+1)`;
  }
  const period = hour < 12 ? "AM" : "PM";
  const display = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${display}:${minute} ${period}`;
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function FeedDashboard({ summary, validation }: Props) {
  const agency = summary.agency[0];
  const rs = summary.route_summary;
  const ss = summary.stop_summary;
  const cs = summary.calendar_summary;
  const ns = summary.network_stats;
  const ts = summary.transfer_summary;

  return (
    <div className="space-y-5">
      {/* Agency header */}
      <div>
        <h2 className="text-lg font-semibold">{agency?.agency_name || "Unknown Agency"}</h2>
        <p className="text-sm text-muted-foreground">
          {agency?.agency_timezone || ""}
          {agency?.agency_url && (
            <>
              {" · "}
              <a href={agency.agency_url} target="_blank" className="hover:text-foreground transition-colors underline">
                Website
              </a>
            </>
          )}
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-2xl font-bold">{formatNumber(ns.total_routes)}</p>
            <p className="text-xs text-muted-foreground mt-1">Routes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-2xl font-bold">{formatNumber(ns.total_stops)}</p>
            <p className="text-xs text-muted-foreground mt-1">Stops</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-2xl font-bold">{formatNumber(ns.total_trips)}</p>
            <p className="text-xs text-muted-foreground mt-1">Trips</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-2xl font-bold">{ts.total_transfers}</p>
            <p className="text-xs text-muted-foreground mt-1">Transfers</p>
          </CardContent>
        </Card>
      </div>

      {/* Transit modes */}
      <div>
        <h3 className="text-sm font-medium mb-2">Transit Modes</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(rs.by_type)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => (
              <Badge key={type} variant="outline" className="font-normal">
                {ROUTE_TYPE_NAMES[parseInt(type)] || `Type ${type}`}: {count}
              </Badge>
            ))}
        </div>
      </div>

      {/* Validation status */}
      <Card className={validation.is_valid ? "border-emerald-200 bg-emerald-50/50" : "border-red-200 bg-red-50/50"}>
        <CardContent className="p-3">
          <p className="text-sm font-medium">
            {validation.is_valid ? "Feed Valid" : "Feed Invalid"}
            <span className="ml-2 text-muted-foreground font-normal">
              {validation.file_count} files ({(validation.total_size_bytes / 1024 / 1024).toFixed(1)} MB)
            </span>
          </p>
          {validation.errors.length > 0 && (
            <ul className="mt-2 space-y-1">
              {validation.errors.map((e, i) => (
                <li key={i} className="text-xs text-red-600">{e}</li>
              ))}
            </ul>
          )}
          {validation.warnings.length > 0 && (
            <ul className="mt-2 space-y-1">
              {validation.warnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-600">{w}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Calendar info */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-3">
            <p className="text-sm font-medium">{cs.weekday_services}</p>
            <p className="text-xs text-muted-foreground">Weekday services</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <p className="text-sm font-medium">{cs.weekend_services}</p>
            <p className="text-xs text-muted-foreground">Weekend services</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <p className="text-sm font-medium">
              {cs.date_range.length === 2 ? `${cs.date_range[0]} — ${cs.date_range[1]}` : "N/A"}
            </p>
            <p className="text-xs text-muted-foreground">Service dates</p>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Routes table */}
      <div>
        <h3 className="text-sm font-medium mb-2">
          Routes <span className="text-muted-foreground font-normal">(showing {Math.min(rs.routes.length, 50)} of {rs.total_routes})</span>
        </h3>
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40">
                <th className="text-left px-3 py-2 font-medium">Route</th>
                <th className="text-left px-3 py-2 font-medium">Name</th>
                <th className="text-left px-3 py-2 font-medium">Type</th>
                <th className="text-right px-3 py-2 font-medium">Trips</th>
                <th className="text-right px-3 py-2 font-medium">Stops</th>
                <th className="text-left px-3 py-2 font-medium">Service</th>
              </tr>
            </thead>
            <tbody>
              {rs.routes.map((route) => (
                <tr key={route.route_id} className="border-b last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2 font-mono text-xs">
                    {route.route_short_name || route.route_id}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground max-w-[200px] truncate">
                    {route.route_long_name || "-"}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      {ROUTE_TYPE_NAMES[route.route_type] || `Type ${route.route_type}`}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {route.trip_count != null ? formatNumber(route.trip_count) : "-"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {route.stop_count ?? "-"}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {route.first_departure && route.last_departure
                      ? `${formatTime(route.first_departure)} – ${formatTime(route.last_departure)}`
                      : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
