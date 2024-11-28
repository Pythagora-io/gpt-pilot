import axios, { AxiosResponse } from "axios";

export const fetchData = async (url: string): Promise<any> => {
  try {
    const response: AxiosResponse = await axios.get(url);
    return response.data;
  } catch (error: unknown) {
    console.error("Error fetching data:", error);
    throw error;
  }
};