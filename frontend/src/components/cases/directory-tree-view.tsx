"use client";

import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  FileText,
  Folder,
  FolderOpen,
  Search,
  ChevronRight,
  ChevronDown,
  List,
  Network,
  MoreVertical,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Document } from "@/types";

interface DirectoryTreeViewProps {
  documents: Document[];
  basePath: string;
  onPreviewDocument?: (docId: string) => void;
}

type ViewMode = "tree" | "list";

interface FolderNode {
  path: string;
  name: string;
  files: Document[];
  subfolders: Map<string, FolderNode>;
  isExpanded: boolean;
}

export function DirectoryTreeView({ documents, basePath, onPreviewDocument }: DirectoryTreeViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("tree");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  // File actions menu component
  const FileActionsMenu = ({ doc }: { doc: Document }) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
        <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={(e) => {
          e.stopPropagation();
          onPreviewDocument?.(doc.id);
        }}>
          <Eye className="h-4 w-4 mr-2" />
          Visualiser
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  // Build folder tree structure
  const folderTree = useMemo(() => {
    const root: FolderNode = {
      path: "",
      name: "root",
      files: [],
      subfolders: new Map(),
      isExpanded: true,
    };

    documents.forEach((doc) => {
      const linkedSource = doc.linked_source;
      if (!linkedSource) return;

      const parentFolder = linkedSource.parent_folder || "root";
      const folders = parentFolder === "root" ? [] : parentFolder.split("/");

      let currentNode = root;

      // Navigate/create folder structure
      folders.forEach((folderName: string) => {
        if (!currentNode.subfolders.has(folderName)) {
          currentNode.subfolders.set(folderName, {
            path: currentNode.path ? `${currentNode.path}/${folderName}` : folderName,
            name: folderName,
            files: [],
            subfolders: new Map(),
            isExpanded: false,
          });
        }
        currentNode = currentNode.subfolders.get(folderName)!;
      });

      // Add file to the current folder
      currentNode.files.push(doc);
    });

    return root;
  }, [documents]);

  // Filter documents by search query
  const filteredDocuments = useMemo(() => {
    if (!searchQuery) return documents;

    const query = searchQuery.toLowerCase();
    return documents.filter(
      (doc) =>
        doc.nom_fichier.toLowerCase().includes(query) ||
        doc.linked_source?.parent_folder?.toLowerCase().includes(query)
    );
  }, [documents, searchQuery]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalSize = documents.reduce((sum, doc) => sum + (doc.taille || 0), 0);
    const folders = new Set<string>();

    documents.forEach((doc) => {
      if (doc.linked_source?.parent_folder) {
        folders.add(doc.linked_source.parent_folder);
      }
    });

    return {
      totalFiles: documents.length,
      totalFolders: folders.size,
      totalSize,
    };
  }, [documents]);

  // Toggle folder expansion
  const toggleFolder = (folderPath: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath);
    } else {
      newExpanded.add(folderPath);
    }
    setExpandedFolders(newExpanded);
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  // Get file extension
  const getFileExtension = (filename: string) => {
    const parts = filename.split(".");
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
  };

  // Render folder node recursively (tree view)
  const renderFolderNode = (node: FolderNode, depth: number = 0) => {
    const isExpanded = expandedFolders.has(node.path) || depth === 0;
    const hasSubfolders = node.subfolders.size > 0;
    const totalFiles = node.files.length;

    if (depth === 0) {
      // Root node - just render children
      return (
        <div className="space-y-1">
          {/* Files in root */}
          {node.files.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-2 py-2 px-3 hover:bg-muted rounded text-sm"
              style={{ paddingLeft: `${(depth + 1) * 12 + 12}px` }}
            >
              <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
              <span className="flex-1 truncate">{doc.nom_fichier}</span>
              <Badge variant="outline" className="text-xs shrink-0">
                {getFileExtension(doc.nom_fichier).toUpperCase()}
              </Badge>
              <span className="text-xs text-muted-foreground shrink-0">
                {formatFileSize(doc.taille)}
              </span>
              <FileActionsMenu doc={doc} />
            </div>
          ))}

          {/* Subfolders */}
          {Array.from(node.subfolders.values()).map((subfolder) =>
            renderFolderNode(subfolder, depth)
          )}
        </div>
      );
    }

    return (
      <div key={node.path}>
        {/* Folder header */}
        <div
          className="flex items-center gap-2 py-2 px-3 hover:bg-muted rounded cursor-pointer"
          style={{ paddingLeft: `${depth * 12 + 12}px` }}
          onClick={() => toggleFolder(node.path)}
        >
          {hasSubfolders && (
            <div className="shrink-0">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          )}
          {!hasSubfolders && <div className="w-4 shrink-0" />}
          {isExpanded ? (
            <FolderOpen className="h-4 w-4 text-blue-500 shrink-0" />
          ) : (
            <Folder className="h-4 w-4 text-blue-500 shrink-0" />
          )}
          <span className="font-medium text-sm flex-1">{node.name}</span>
          <Badge variant="outline" className="text-xs shrink-0">
            {totalFiles} fichier{totalFiles > 1 ? "s" : ""}
          </Badge>
        </div>

        {/* Folder contents (when expanded) */}
        {isExpanded && (
          <div className="space-y-1">
            {/* Files */}
            {node.files.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-2 py-2 px-3 hover:bg-muted rounded text-sm"
                style={{ paddingLeft: `${(depth + 1) * 12 + 12}px` }}
              >
                <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="flex-1 truncate">{doc.nom_fichier}</span>
                <Badge variant="outline" className="text-xs shrink-0">
                  {getFileExtension(doc.nom_fichier).toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatFileSize(doc.taille)}
                </span>
                <FileActionsMenu doc={doc} />
              </div>
            ))}

            {/* Subfolders */}
            {Array.from(node.subfolders.values()).map((subfolder) =>
              renderFolderNode(subfolder, depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  // Render list view
  const renderListView = () => {
    const displayDocuments = searchQuery ? filteredDocuments : documents;

    // Group by folder
    const byFolder = displayDocuments.reduce((acc, doc) => {
      const folder = doc.linked_source?.parent_folder || "root";
      if (!acc[folder]) {
        acc[folder] = [];
      }
      acc[folder].push(doc);
      return acc;
    }, {} as Record<string, Document[]>);

    const folders = Object.keys(byFolder).sort();

    return (
      <div className="space-y-4">
        {folders.map((folder) => (
          <div key={folder}>
            <div className="flex items-center gap-2 py-2 px-3 bg-muted rounded mb-1">
              <Folder className="h-4 w-4 text-blue-500" />
              <span className="font-medium text-sm flex-1">
                {folder === "root" ? "/" : folder}
              </span>
              <Badge variant="outline" className="text-xs">
                {byFolder[folder].length}
              </Badge>
            </div>
            <div className="space-y-1">
              {byFolder[folder].map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-2 py-2 px-3 hover:bg-muted rounded text-sm ml-6"
                >
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="flex-1 truncate">{doc.nom_fichier}</span>
                  <Badge variant="outline" className="text-xs shrink-0">
                    {getFileExtension(doc.nom_fichier).toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {formatFileSize(doc.taille)}
                  </span>
                  <FileActionsMenu doc={doc} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with statistics */}
      <div className="grid grid-cols-3 gap-4 p-4 bg-muted rounded-lg mb-4">
        <div className="text-center">
          <p className="text-2xl font-bold">{stats.totalFiles}</p>
          <p className="text-xs text-muted-foreground">Fichiers</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold">{stats.totalFolders}</p>
          <p className="text-xs text-muted-foreground">Dossiers</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold">{formatFileSize(stats.totalSize)}</p>
          <p className="text-xs text-muted-foreground">Taille totale</p>
        </div>
      </div>

      {/* View mode toggle and search */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex border rounded-md">
          <Button
            variant={viewMode === "tree" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("tree")}
            className="rounded-r-none"
          >
            <Network className="h-4 w-4 mr-2" />
            Vue arbre
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("list")}
            className="rounded-l-none"
          >
            <List className="h-4 w-4 mr-2" />
            Vue liste
          </Button>
        </div>

        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher un fichier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Directory path */}
      <div className="p-3 bg-muted rounded text-xs font-mono break-all mb-4">
        {basePath}
      </div>

      {/* File tree/list */}
      <ScrollArea className="flex-1">
        {viewMode === "tree" ? renderFolderNode(folderTree) : renderListView()}
      </ScrollArea>
    </div>
  );
}
