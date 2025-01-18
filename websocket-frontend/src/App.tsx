import { useEffect, useState } from "react";
import { Socket, io } from "socket.io-client";
import axios from "axios";
import {
  Container,
  TextInput,
  Textarea,
  Button,
  Paper,
  Title,
  Stack,
  Card,
  Text,
  Alert,
  Badge,
} from "@mantine/core";

interface Item {
  _id: string;
  name: string;
  description: string;
  createdAt: string;
}

function App() {
  const [, setSocket] = useState<Socket | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";
  const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:3000";

  useEffect(() => {
    const newSocket = io(WS_URL, {
      withCredentials: true,
      transports: ["websocket", "polling"],
    });

    setSocket(newSocket);

    // Connection status handlers
    newSocket.on("connect", () => {
      setIsConnected(true);
      setError(null);
      setLastUpdate(new Date().toLocaleString());
      console.log("Connected to websocket");
      fetchItems();
    });

    newSocket.on("disconnect", () => {
      setIsConnected(false);
      setLastUpdate(new Date().toLocaleString());
      console.log("Disconnected from websocket");
    });

    newSocket.on("connect_error", (error) => {
      console.log("Connection error:", error);
      setError(`Connection error: ${error.message}`);
      setIsConnected(false);
      setLastUpdate(new Date().toLocaleString());
    });

    // Item change handlers
    newSocket.on("itemCreated", (item: Item) => {
      console.log("New item received:", item);
      setItems((prev) =>
        [...prev, item].sort(
          (a, b) =>
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        )
      );
      setLastUpdate(new Date().toLocaleString());
    });

    newSocket.on("itemUpdated", (updatedItem: Item) => {
      console.log("Item updated:", updatedItem);
      setItems((prev) =>
        prev.map((item) => (item._id === updatedItem._id ? updatedItem : item))
      );
      setLastUpdate(new Date().toLocaleString());
    });

    newSocket.on("itemDeleted", (deletedItemId: string) => {
      console.log("Item deleted:", deletedItemId);
      setItems((prev) => prev.filter((item) => item._id !== deletedItemId));
      setLastUpdate(new Date().toLocaleString());
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  const fetchItems = async () => {
    try {
      const response = await axios.get(`${API_URL}/items`, {
        withCredentials: true,
      });
      const sortedItems = response.data.sort(
        (a: Item, b: Item) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      );
      setItems(sortedItems);
      setError(null);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An error occurred";
      setError(`Error fetching items: ${errorMessage}`);
      console.error("Error fetching items:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(
        `${API_URL}/items`,
        {
          name,
          description,
        },
        {
          withCredentials: true,
        }
      );
      setName("");
      setDescription("");
      setError(null);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An error occurred";
      setError(`Error creating item: ${errorMessage}`);
      console.error("Error creating item:", error);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title order={1} mb="xl">
        Real-time Items List{" "}
        <Badge color={isConnected ? "green" : "red"} variant="light">
          {isConnected ? "Connected" : "Disconnected"}
        </Badge>
      </Title>

      {error && (
        <Alert color="red" mb="lg" title="Error">
          {error}
        </Alert>
      )}

      {lastUpdate && (
        <Text size="sm" c="dimmed" mb="md">
          Last update: {lastUpdate}
        </Text>
      )}

      <Paper p="md" mb="xl" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
            <Button type="submit" disabled={!isConnected}>
              {isConnected ? "Add Item" : "Connecting..."}
            </Button>
          </Stack>
        </form>
      </Paper>

      <Stack>
        {items.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No items yet. Create one to get started!
          </Text>
        ) : (
          items.map((item) => (
            <Card key={item._id} withBorder>
              <Text fw={500}>{item.name}</Text>
              <Text c="dimmed" size="sm">
                {item.description}
              </Text>
              <Text size="xs" c="dimmed" mt="sm">
                Created: {new Date(item.createdAt).toLocaleString()}
              </Text>
            </Card>
          ))
        )}
      </Stack>
    </Container>
  );
}

export default App;
