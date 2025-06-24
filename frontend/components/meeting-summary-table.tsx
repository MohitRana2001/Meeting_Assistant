"use client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDistanceToNow } from "date-fns";
import { ExternalLink, CheckCircle2 } from "lucide-react";
import { MeetingSummary } from "@/lib/api";

interface MeetingSummaryTableProps {
  summaries: MeetingSummary[];
  onRowSelect: (summary: MeetingSummary) => void;
  selectedSummary?: MeetingSummary;
}

export function MeetingSummaryTable({
  summaries,
  onRowSelect,
  selectedSummary,
}: MeetingSummaryTableProps) {
  const truncateText = (text: string, maxLength = 120) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + "...";
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm">
      <Table>
        <TableHeader className="bg-gray-50/50">
          <TableRow className="border-b border-gray-200">
            <TableHead className="font-semibold text-gray-900 text-sm">
              Created At
            </TableHead>
            <TableHead className="font-semibold text-gray-900 text-sm">
              Meeting Title
            </TableHead>
            <TableHead className="font-semibold text-gray-900 text-sm">
              Summary
            </TableHead>
            <TableHead className="font-semibold text-gray-900 text-sm">
              Tasks
            </TableHead>
            <TableHead className="font-semibold text-gray-900 text-sm">
              Action
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {summaries.map((summary) => (
            <TableRow
              key={summary.id}
              className={`cursor-pointer hover:bg-gray-50/50 transition-colors ${
                selectedSummary?.id === summary.id
                  ? "bg-indigo-50 border-l-4 border-l-indigo-500"
                  : ""
              }`}
              onClick={() => onRowSelect(summary)}
            >
              <TableCell className="text-sm text-gray-600">
                {formatDistanceToNow(new Date(summary.createdAt), {
                  addSuffix: true,
                })}
              </TableCell>
              <TableCell className="font-medium text-gray-900 text-sm">
                {summary.title}
              </TableCell>
              <TableCell className="text-sm text-gray-600 max-w-md">
                <div className="line-clamp-2">
                  {truncateText(summary.summary)}
                </div>
              </TableCell>
              <TableCell className="text-sm">
                <div className="flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4 text-gray-400" />
                  <span className="text-gray-600">{summary.tasks.length}</span>
                </div>
              </TableCell>
              <TableCell>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs font-medium bg-white hover:bg-gray-50"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRowSelect(summary);
                  }}
                >
                  Open
                  <ExternalLink className="ml-1 h-3 w-3" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
