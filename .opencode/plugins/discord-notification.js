import { config } from "dotenv"
config({ path: ".env" })

export const DiscordNotificationPlugin = async ({ project }) => {
  const webhookUrl = process.env.DISCORD_WEBHOOK_URL || process.env.SCANNERS_NOTIFICATIONS_DISCORD_WEBHOOK_URL

  if (!webhookUrl) {
    console.warn("Discord webhook URL not configured. Set DISCORD_WEBHOOK_URL environment variable.")
    return {}
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const projectName = project?.name || "Unknown Project"

        const payload = {
          content: `Session completed in **${projectName}**`,
          embeds: [
            {
              title: "OpenCode Session Idle",
              description: "The AI assistant has finished processing and is waiting for input.",
              color: 5814783,
              fields: [{ name: "Project", value: projectName, inline: true }],
              timestamp: new Date().toISOString(),
            },
          ],
        }

        try {
          await fetch(webhookUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          })
        } catch (error) {
          console.error("Failed to send Discord notification:", error.message)
        }
      }
    },
  }
}
