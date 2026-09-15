/**
 * Entry point. `node dist/server/main.js --stdio` serves Claude Desktop's local
 * (claude_desktop_config.json) connection; without the flag, or with
 * MCP_TRANSPORT=http, it serves Streamable HTTP on PORT (default 3001) at /mcp for a
 * remote custom connector.
 */
import { createMcpExpressApp } from "@modelcontextprotocol/express";
import { NodeStreamableHTTPServerTransport } from "@modelcontextprotocol/node";
import type { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import cors from "cors";
import type { Request, Response } from "express";
import { createServer } from "./server.js";

export async function startStreamableHTTPServer(factory: () => McpServer): Promise<void> {
  const port = parseInt(process.env.PORT ?? "3001", 10);
  const app = createMcpExpressApp({ host: "0.0.0.0" });
  app.use(cors());

  app.all("/mcp", async (req: Request, res: Response) => {
    const server = factory();
    const transport = new NodeStreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    res.on("close", () => {
      transport.close().catch(() => {});
      server.close().catch(() => {});
    });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error("MCP error:", error);
      if (!res.headersSent) {
        res.status(500).json({ jsonrpc: "2.0", error: { code: -32603, message: "Internal server error" }, id: null });
      }
    }
  });

  const httpServer = app.listen(port, () => {
    console.log(`LOS Demo Setup card listening on http://localhost:${port}/mcp`);
  });
  const shutdown = () => httpServer.close(() => process.exit(0));
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

export async function startStdioServer(factory: () => McpServer): Promise<void> {
  await factory().connect(new StdioServerTransport());
}

async function main(): Promise<void> {
  const stdio = process.argv.includes("--stdio") || process.env.MCP_TRANSPORT === "stdio";
  if (stdio) await startStdioServer(createServer);
  else await startStreamableHTTPServer(createServer);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
